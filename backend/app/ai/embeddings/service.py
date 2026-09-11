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

# Separate cooldown tracker for embedding models (independent from chat cooldowns)
_embedding_cooldowns: dict[str, float] = {}


def _parse_retry_delay(exc: Exception) -> float | None:
    """Extract retryDelay from Gemini API error responses (e.g. '30s')."""
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
        return _GEMINI_EMBEDDING_DIMENSIONS.get(self._model, 3072)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        max_retries = 3
        for attempt in range(max_retries):
            if _is_embedding_cooling_down(self._model):
                cooldown_left = _embedding_cooldowns[self._model] - time.time()
                if cooldown_left > 0:
                    logger.info("Embedding model in cooldown, waiting %.0fs...", cooldown_left)
                    await asyncio.sleep(min(cooldown_left, 30))

            try:
                sem = asyncio.Semaphore(5)

                async def _embed_single(text: str) -> list[float]:
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
                            return list(values)
                        raise AIServiceError("The AI provider returned empty embeddings.")

                return await asyncio.gather(*[_embed_single(text) for text in texts])

            except APIError as exc:
                if _is_rate_limit_error(exc):
                    retry_delay = _parse_retry_delay(exc)
                    _set_embedding_cooldown(self._model, retry_delay)
                    wait = retry_delay or min(2 ** attempt * 5, 60)
                    logger.warning(
                        "Embedding rate limited (attempt %d/%d). Waiting %.0fs before retry...",
                        attempt + 1, max_retries, wait,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait)
                        continue
                raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
            except Exception as exc:
                raise AIServiceError(f"The AI provider request failed: {exc}") from exc

        raise AIServiceError("Embedding failed after all retries.")


# Backward compatibility alias
OpenAIEmbeddingProvider = GeminiEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
