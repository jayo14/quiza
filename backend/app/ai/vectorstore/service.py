from sqlalchemy.orm import Session

from app.ai.vectorstore.base import VectorStore
from app.core.config import settings


def get_vector_store(db: Session) -> VectorStore:
    if settings.vector_store_backend == "sqlite":
        from app.ai.vectorstore.sqlite_store import SQLiteVectorStore

        return SQLiteVectorStore(db)
    if settings.vector_store_backend == "pgvector":
        from app.ai.vectorstore.pgvector_store import PgVectorStore

        return PgVectorStore(db)
    raise ValueError(f"Unsupported vector store backend: {settings.vector_store_backend}")
