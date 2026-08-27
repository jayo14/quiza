from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

_OPENAI_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = model or settings.openai_embedding_model

    @property
    def dimensions(self) -> int:
        return _OPENAI_EMBEDDING_DIMENSIONS.get(self._model, 1536)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(model=self._model, input=texts)
        except RateLimitError as exc:
            raise AIServiceError("The AI provider is rate-limiting requests, try again shortly.") from exc
        except APITimeoutError as exc:
            raise AIServiceError("The AI provider timed out.") from exc
        except APIError as exc:
            raise AIServiceError(f"The AI provider returned an error: {exc}") from exc

        return [item.embedding for item in response.data]


def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider()
