from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstraction over a text-embedding model. The RAG pipeline depends only on
    this interface so the embedding backend can be swapped independently of the
    LLM provider."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input in the same order."""
        raise NotImplementedError

    def validate_dimensions(self, embedding: list[float]) -> None:
        if len(embedding) != self.dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(embedding)}"
            )

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]
