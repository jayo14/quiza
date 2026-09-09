import asyncio

from google import genai
from google.genai.errors import APIError

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

_GEMINI_EMBEDDING_DIMENSIONS = {
    "gemini-embedding-001": 3072,
    "gemini-embedding-2": 3072,
    "text-embedding-004": 768,
    "embedding-001": 768,
}


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
            raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
        except Exception as exc:
            raise AIServiceError(f"The AI provider request failed: {exc}") from exc


# Backward compatibility alias
OpenAIEmbeddingProvider = GeminiEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
