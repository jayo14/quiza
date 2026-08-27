from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Summary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summaries"

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Validated, structured summary content (see schemas.summary.SummaryContent).
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    raw_ai_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="summary")
