import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.vectorstore.base import EmbeddingRecord, SearchResult, VectorStore
from app.ai.vectorstore.models import ChunkEmbedding


class SQLiteVectorStore(VectorStore):
    """Brute-force cosine-similarity search over embeddings stored as JSON in a
    regular SQLite table. Fine for local development and small-to-medium corpora;
    swap VECTOR_STORE_BACKEND to pgvector for real ANN search in production."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add_many(self, records: list[EmbeddingRecord], *, commit: bool = True) -> None:
        for record in records:
            self._db.merge(
                ChunkEmbedding(
                    chunk_id=record.chunk_id,
                    material_id=record.material_id,
                    user_id=record.user_id,
                    embedding=record.embedding,
                )
            )
        if commit:
            self._db.commit()

    def search(
        self,
        *,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[SearchResult]:
        stmt = select(ChunkEmbedding).where(ChunkEmbedding.user_id == user_id)
        if material_id is not None:
            stmt = stmt.where(ChunkEmbedding.material_id == material_id)

        candidates = self._db.scalars(stmt).all()
        if not candidates:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)

        scored: list[SearchResult] = []
        for candidate in candidates:
            candidate_vec = np.array(candidate.embedding, dtype=np.float32)
            if query_vec.shape != candidate_vec.shape:
                raise ValueError(
                    f"Embedding dimension mismatch: query={len(query_vec)}, candidate={len(candidate_vec)}"
                )

            q_norm = np.linalg.norm(query_vec) or 1e-9
            c_norm = np.linalg.norm(candidate_vec) or 1e-9
            similarity = float(np.dot(query_vec, candidate_vec) / (q_norm * c_norm))
            scored.append(SearchResult(chunk_id=candidate.chunk_id, score=similarity))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def delete_material(self, *, material_id: str, user_id: str, commit: bool = True) -> None:
        self._db.execute(
            delete(ChunkEmbedding).where(
                ChunkEmbedding.material_id == material_id, ChunkEmbedding.user_id == user_id
            )
        )
        if commit:
            self._db.commit()
