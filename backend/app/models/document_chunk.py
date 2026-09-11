from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Relational metadata + text for one chunk. The embedding vector itself lives
    in the vector store (see app/ai/vectorstore), keyed by this row's id, so the
    vector backend can be swapped without touching this table."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("material_id", "chunk_index", name="uq_document_chunks_material_index"),
        Index("ix_document_chunks_user_material", "user_id", "material_id"),
    )

    material_id: Mapped[str] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    material: Mapped["Material"] = relationship(back_populates="chunks")
