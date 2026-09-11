from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingRecord:
    chunk_id: str
    material_id: str
    user_id: str
    embedding: list[float]


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float


class VectorStore(ABC):
    """Abstraction over vector storage + similarity search. Every record is tagged
    with `user_id` and `material_id`, and `search` REQUIRES a `user_id` filter so a
    caller can never retrieve another student's chunks even by mistake — that
    isolation guarantee lives here, not in the caller."""

    @abstractmethod
    def add_many(self, records: list[EmbeddingRecord], *, commit: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        *,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_material(self, *, material_id: str, user_id: str, commit: bool = True) -> None:
        raise NotImplementedError
