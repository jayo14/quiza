from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ErrorType, RecommendedAction, Severity


class Answer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "answers"
    __table_args__ = (Index("ix_answers_attempt_question", "attempt_id", "question_id", unique=True),)

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_taken_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)

    # Structured, validated mistake analysis (see app/ai/answer_analyzer.py). Null until
    # analysis runs, and left null entirely for correct answers.
    error_type: Mapped[ErrorType | None] = mapped_column(
        Enum(ErrorType, native_enum=False, length=32), nullable=True
    )
    misconception: Mapped[str | None] = mapped_column(Text, nullable=True)
    mistake_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[Severity | None] = mapped_column(
        Enum(Severity, native_enum=False, length=16), nullable=True
    )
    recommended_action: Mapped[RecommendedAction | None] = mapped_column(
        Enum(RecommendedAction, native_enum=False, length=32), nullable=True
    )
    # Raw AI response kept for debugging/auditing, never returned to the client directly.
    raw_ai_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")
