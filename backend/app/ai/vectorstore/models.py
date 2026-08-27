from sqlalchemy import ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChunkEmbedding(TimestampMixin, Base):
    """Embedding storage for the SQLite vector store backend. The primary key mirrors
    the owning DocumentChunk's id 1:1 rather than using a surrogate key. Kept in its
    own table (not on DocumentChunk itself) so a Postgres/pgvector deployment can
    swap this out entirely without altering document_chunks."""

    __tablename__ = "chunk_embeddings"
    __table_args__ = (Index("ix_chunk_embeddings_user_material", "user_id", "material_id"),)

    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    material_id: Mapped[str] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
