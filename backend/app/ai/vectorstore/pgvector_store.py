from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.vectorstore.base import EmbeddingRecord, SearchResult, VectorStore


def _get_embedding_dimension() -> int:
    from app.ai.embeddings.service import _GEMINI_EMBEDDING_DIMENSIONS
    from app.core.config import settings
    model = settings.gemini_embedding_model
    return _GEMINI_EMBEDDING_DIMENSIONS.get(model, 768)


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

    def add_many(self, records: list[EmbeddingRecord], *, commit: bool = True) -> None:
        expected_dim = _get_embedding_dimension()
        for record in records:
            emb = record.embedding
            # Truncate or zero-pad to expected dimension
            if len(emb) > expected_dim:
                emb = emb[:expected_dim]
            elif len(emb) < expected_dim:
                emb = emb + [0.0] * (expected_dim - len(emb))
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
                    "embedding": emb,
                },
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
        if not query_embedding:
            raise ValueError("query_embedding must not be empty")

        if not all(isinstance(v, (int, float)) for v in query_embedding):
            raise ValueError("query_embedding must contain only numeric values")
        material_filter = "AND material_id = :material_id" if material_id else ""
        vector_str = "[" + ",".join(format(v, "g") for v in query_embedding) + "]"
        rows = self._db.execute(
            text(
                f"""
                SELECT chunk_id, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM chunk_embeddings_vector
                WHERE user_id = :user_id {material_filter}
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            ),
            {
                "query_embedding": vector_str,
                "user_id": user_id,
                "material_id": material_id,
                "top_k": top_k,
            },
        )
        return [SearchResult(chunk_id=row.chunk_id, score=row.score) for row in rows]

    def delete_material(self, *, material_id: str, user_id: str, commit: bool = True) -> None:
        self._db.execute(
            text(
                "DELETE FROM chunk_embeddings_vector WHERE material_id = :material_id AND user_id = :user_id"
            ),
            {"material_id": material_id, "user_id": user_id},
        )
        if commit:
            self._db.commit()
