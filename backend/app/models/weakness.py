from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Severity


class Weakness(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "weaknesses"
    __table_args__ = (
        Index("ix_weaknesses_user_topic_concept", "user_id", "topic", "concept", unique=True),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    concept: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mistake_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, native_enum=False, length=16), default=Severity.LOW
    )
    last_seen: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="weaknesses")
