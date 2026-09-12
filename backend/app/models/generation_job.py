from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GenerationJobStatus


class GenerationJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index("ix_generation_jobs_user_status", "user_id", "status"),
        Index("ix_generation_jobs_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[GenerationJobStatus] = mapped_column(
        Enum(GenerationJobStatus, native_enum=False, length=16),
        default=GenerationJobStatus.QUEUED,
        nullable=False,
    )
    material_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    question_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    quiz_id: Mapped[str | None] = mapped_column(
        ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="generation_jobs")
    quiz: Mapped["Quiz | None"] = relationship(back_populates="generation_job")
