import logging
import random
import asyncio
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

_EMBED_BATCH_SIZE = 100
_EMBED_BATCH_DELAY = 0.5  # seconds between batches
_MAX_RETRIES_PER_MODEL = 3
_MAX_RETRIES_QUOTA_EXHAUSTED = 5

_embedding_cooldowns: dict[str, float] = {}
_quota_exhausted_models: dict[str, float] = {}
_quota_exhausted_ttl = 3600  # treat quota exhaustion for 1 hour


def _parse_retry_delay(exc: Exception) -> float | None:
    msg = str(exc)
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", msg)
    if match:
        return float(match.group(1))
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(indicator in msg for indicator in ["429", "resource_exhausted", "rate_limit", "quota"])


def _is_quota_exhausted(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "quota" in msg and "exceeded" in msg


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


def _mark_quota_exhausted(model: str) -> None:
    _quota_exhausted_models[model] = time.time() + _quota_exhausted_ttl
    logger.warning("Embedding model '%s' marked quota-exhausted for %ds.", model, _quota_exhausted_ttl)


def _is_quota_exhausted(model: str) -> bool:
    return time.time() < _quota_exhausted_models.get(model, 0.0)


def _get_fallback_models(primary: str) -> list[str]:
    raw = getattr(settings, "gemini_embedding_fallback_models", "")
    if not raw:
        return []
    return [m.strip() for m in raw.split(",") if m.strip() and m.strip() != primary]


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str | None = None) -> None:
        self._model = model or settings.gemini_embedding_model
        self._client: genai.Client | None = None
        self._fallback_models = _get_fallback_models(self._model)
        self._active_model = self._model

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aio.close()
            except Exception:
                pass
            self._client = None

    @property
    def dimensions(self) -> int:
        dims = _GEMINI_EMBEDDING_DIMENSIONS.get(self._active_model)
        if dims is None:
            raise ValueError(
                f"Unknown embedding model '{self._active_model}'. "
                f"Known models: {', '.join(_GEMINI_EMBEDDING_DIMENSIONS.keys())}"
            )
        return dims

    async def _embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        target_model = model or self._active_model
        client = self._ensure_client()
        response = await client.aio.models.embed_content(
            model=target_model,
            contents=texts,
        )
        raw_embeddings = getattr(response, "embeddings", None)
        if raw_embeddings is None and getattr(response, "embedding", None) is not None:
            raw_embeddings = [response.embedding]
        values = [list(item.values) for item in (raw_embeddings or []) if getattr(item, "values", None)]
        expected_dims = _GEMINI_EMBEDDING_DIMENSIONS.get(target_model, 0)
        if len(values) != len(texts):
            raise AIServiceError(
                f"The AI provider returned {len(values)} embeddings for {len(texts)} documents."
            )
        for embedding in values:
            if expected_dims and len(embedding) != expected_dims:
                raise AIServiceError(
                    f"Embedding dimension mismatch: expected {expected_dims}, got {len(embedding)}"
                )
        return values

    async def _try_embed_with_model(self, texts: list[str], model: str) -> list[list[float]]:
        """Try embedding all texts with a specific model, respecting batch limits."""
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _EMBED_BATCH_SIZE]
            batch_num = (batch_start // _EMBED_BATCH_SIZE) + 1
            total_batches = (len(texts) + _EMBED_BATCH_SIZE - 1) // _EMBED_BATCH_SIZE
            max_retries = _MAX_RETRIES_QUOTA_EXHAUSTED if _is_quota_exhausted(model) else _MAX_RETRIES_PER_MODEL

            for attempt in range(max_retries):
                if _is_embedding_cooling_down(model):
                    cooldown_left = _embedding_cooldowns[model] - time.time()
                    if cooldown_left > 0:
                        wait = min(cooldown_left, 60)
                        logger.info("Embedding in cooldown, waiting %.0fs...", wait)
                        await asyncio.sleep(wait)

                try:
                    result = await self._embed_batch(batch, model)
                    all_embeddings.extend(result)
                    logger.debug("Embedded batch %d/%d with model %s", batch_num, total_batches, model)
                    break
                except APIError as exc:
                    if _is_rate_limit_error(exc):
                        if _is_quota_exhausted(exc):
                            _mark_quota_exhausted(model)
                            raise  # caller should try next model
                        retry_delay = _parse_retry_delay(exc)
                        _set_embedding_cooldown(model, retry_delay)
                        wait = retry_delay or min(2 ** attempt * 10, 120)
                        logger.warning(
                            "Embedding rate limited on batch %d/%d (attempt %d/%d). Waiting %.0fs...",
                            batch_num, total_batches, attempt + 1, max_retries, wait,
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(wait + random.uniform(0, min(2.0, wait * 0.1)))
                            continue
                    raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
                except Exception as exc:
                    raise AIServiceError(f"The AI provider request failed: {exc}") from exc
            else:
                raise AIServiceError(
                    f"Embedding failed after {max_retries} retries on batch {batch_num}/{total_batches} with model {model}."
                )

            if batch_start + _EMBED_BATCH_SIZE < len(texts):
                await asyncio.sleep(_EMBED_BATCH_DELAY)

        return all_embeddings

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        models_to_try = [self._model] + [m for m in self._fallback_models if m != self._model]
        last_error: Exception | None = None

        for model in models_to_try:
            if _is_quota_exhausted(model):
                logger.info("Skipping quota-exhausted model '%s', trying next...", model)
                continue
            try:
                self._active_model = model
                result = await self._try_embed_with_model(texts, model)
                return result
            except AIServiceError as exc:
                last_error = exc
                if _is_quota_exhausted(str(exc)):
                    logger.warning("Model '%s' quota exhausted, trying fallback...", model)
                    continue
                raise
            except Exception as exc:
                last_error = exc
                logger.warning("Model '%s' failed: %s, trying fallback...", model, exc)
                continue

        raise AIServiceError(
            f"All embedding models exhausted. Last error: {last_error}"
        ) from last_error


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
