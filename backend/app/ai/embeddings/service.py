import asyncio
import logging
import re
import time

from google import genai
from google.genai.errors import APIError

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)

_GEMINI_EMBEDDING_DIMENSIONS = {
    "gemini-embedding-001": 3072,
    "gemini-embedding-2": 3072,
    "text-embedding-004": 768,
    "embedding-001": 768,
}

# Gemini free tier: 100 embedding requests/min. Batch size stays well under.
_EMBED_BATCH_SIZE = 20
_EMBED_BATCH_DELAY = 1.5  # seconds between batches

_embedding_cooldowns: dict[str, float] = {}


def _parse_retry_delay(exc: Exception) -> float | None:
    msg = str(exc)
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", msg)
    if match:
        return float(match.group(1))
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(indicator in msg for indicator in ["429", "resource_exhausted", "rate_limit", "quota"])


def _is_embedding_cooling_down(model: str) -> bool:
    return time.time() < _embedding_cooldowns.get(model, 0.0)


def _set_embedding_cooldown(model: str, duration: float | None = None) -> None:
    cooldown = duration or 60.0
    _embedding_cooldowns[model] = time.time() + cooldown
    logger.warning(
        "Embedding model '%s' placed in cooldown for %ds.",
        model,
        int(cooldown),
    )


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str | None = None) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or settings.gemini_embedding_model

    @property
    def dimensions(self) -> int:
        dims = _GEMINI_EMBEDDING_DIMENSIONS.get(self._model)
        if dims is None:
            raise ValueError(
                f"Unknown embedding model '{self._model}'. "
                f"Known models: {', '.join(_GEMINI_EMBEDDING_DIMENSIONS.keys())}"
            )
        return dims

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts concurrently (up to 5 at a time)."""
        sem = asyncio.Semaphore(5)

        async def _embed_one(text: str) -> list[float]:
            async with sem:
                response = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=text,
                )
                values = None
                if hasattr(response, "embedding") and response.embedding and getattr(response.embedding, "values", None):
                    values = response.embedding.values
                elif hasattr(response, "embeddings") and response.embeddings and len(response.embeddings) > 0:
                    values = response.embeddings[0].values

                if values:
                    result = list(values)
                    if len(result) != self.dimensions:
                        raise AIServiceError(
                            f"Embedding dimension mismatch: expected {self.dimensions}, got {len(result)}"
                        )
                    return result
                raise AIServiceError("The AI provider returned empty embeddings.")

        return await asyncio.gather(*[_embed_one(text) for text in texts])

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        max_retries = 3
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _EMBED_BATCH_SIZE]
            batch_num = (batch_start // _EMBED_BATCH_SIZE) + 1
            total_batches = (len(texts) + _EMBED_BATCH_SIZE - 1) // _EMBED_BATCH_SIZE

            for attempt in range(max_retries):
                if _is_embedding_cooling_down(self._model):
                    cooldown_left = _embedding_cooldowns[self._model] - time.time()
                    if cooldown_left > 0:
                        wait = min(cooldown_left, 60)
                        logger.info("Embedding in cooldown, waiting %.0fs...", wait)
                        await asyncio.sleep(wait)

                try:
                    result = await self._embed_batch(batch)
                    all_embeddings.extend(result)
                    logger.debug("Embedded batch %d/%d (%d texts)", batch_num, total_batches, len(batch))
                    break
                except APIError as exc:
                    if _is_rate_limit_error(exc):
                        retry_delay = _parse_retry_delay(exc)
                        _set_embedding_cooldown(self._model, retry_delay)
                        wait = retry_delay or min(2 ** attempt * 10, 60)
                        logger.warning(
                            "Embedding rate limited on batch %d/%d (attempt %d/%d). Waiting %.0fs...",
                            batch_num, total_batches, attempt + 1, max_retries, wait,
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(wait)
                            continue
                    raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
                except Exception as exc:
                    raise AIServiceError(f"The AI provider request failed: {exc}") from exc
            else:
                raise AIServiceError(f"Embedding failed after {max_retries} retries on batch {batch_num}/{total_batches}.")

            # Delay between batches to stay under rate limit
            if batch_start + _EMBED_BATCH_SIZE < len(texts):
                await asyncio.sleep(_EMBED_BATCH_DELAY)

        return all_embeddings


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
