from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Lightweight per-user topic registry, used to dedupe topic names surfaced by
    quiz generation and mistake analysis before they feed the weakness engine."""

    __tablename__ = "topics"
    __table_args__ = (Index("ix_topics_user_name", "user_id", "name", unique=True),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
