from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Difficulty, QuizStatus


class Quiz(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quizzes"
    __table_args__ = (Index("ix_quizzes_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[str] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, native_enum=False, length=16), nullable=False
    )
    status: Mapped[QuizStatus] = mapped_column(
        Enum(QuizStatus, native_enum=False, length=16), default=QuizStatus.GENERATING
    )
    generation_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user: Mapped["User"] = relationship(back_populates="quizzes")
    material: Mapped["Material"] = relationship(back_populates="quizzes")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_index"
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="quiz")
