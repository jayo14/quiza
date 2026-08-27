from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.vectorstore.base import EmbeddingRecord, SearchResult, VectorStore


class PgVectorStore(VectorStore):
    """Postgres + pgvector backend for production scale. Requires the `pgvector`
    extension enabled on the database and the `pgvector` python package installed;
    both are optional for local SQLite development, which is why the import and the
    extension check are deferred to construction time rather than module load.

    This mirrors SQLiteVectorStore's contract exactly so RAG ingestion/retrieval
    code never needs to know which backend is active.
    """

    def __init__(self, db: Session) -> None:
        try:
            import pgvector.sqlalchemy  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "PgVectorStore requires the 'pgvector' package. Install it and enable "
                "the pgvector extension on your Postgres database, then set "
                "VECTOR_STORE_BACKEND=pgvector."
            ) from exc
        self._db = db

    def add_many(self, records: list[EmbeddingRecord]) -> None:
        for record in records:
            self._db.execute(
                text(
                    """
                    INSERT INTO chunk_embeddings_vector (chunk_id, material_id, user_id, embedding)
                    VALUES (:chunk_id, :material_id, :user_id, :embedding)
                    ON CONFLICT (chunk_id) DO UPDATE SET embedding = EXCLUDED.embedding
                    """
                ),
                {
                    "chunk_id": record.chunk_id,
                    "material_id": record.material_id,
                    "user_id": record.user_id,
                    "embedding": record.embedding,
                },
            )
        self._db.commit()

    def search(
        self,
        *,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        material_id: str | None = None,
    ) -> list[SearchResult]:
        material_filter = "AND material_id = :material_id" if material_id else ""
        rows = self._db.execute(
            text(
                f"""
                SELECT chunk_id, 1 - (embedding <=> :query_embedding) AS score
                FROM chunk_embeddings_vector
                WHERE user_id = :user_id {material_filter}
                ORDER BY embedding <=> :query_embedding
                LIMIT :top_k
                """
            ),
            {
                "query_embedding": query_embedding,
                "user_id": user_id,
                "material_id": material_id,
                "top_k": top_k,
            },
        )
        return [SearchResult(chunk_id=row.chunk_id, score=row.score) for row in rows]

    def delete_material(self, *, material_id: str, user_id: str) -> None:
        self._db.execute(
            text(
                "DELETE FROM chunk_embeddings_vector WHERE material_id = :material_id AND user_id = :user_id"
            ),
            {"material_id": material_id, "user_id": user_id},
        )
        self._db.commit()
