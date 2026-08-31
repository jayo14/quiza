from google import genai
from google.genai.errors import APIError

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

_GEMINI_EMBEDDING_DIMENSIONS = {
    "text-embedding-004": 768,
    "embedding-001": 768,
}


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str | None = None) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or settings.gemini_embedding_model

    @property
    def dimensions(self) -> int:
        return _GEMINI_EMBEDDING_DIMENSIONS.get(self._model, 768)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            embeddings: list[list[float]] = []
            # Batch process texts with Google GenAI SDK
            for text in texts:
                response = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=text,
                )
                if response.embedding and response.embedding.values:
                    embeddings.append(response.embedding.values)
                else:
                    raise AIServiceError("The AI provider returned empty embeddings.")
            return embeddings
        except APIError as exc:
            raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
        except Exception as exc:
            raise AIServiceError(f"The AI provider request failed: {exc}") from exc


# Backward compatibility alias
OpenAIEmbeddingProvider = GeminiEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
