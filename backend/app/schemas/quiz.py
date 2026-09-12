from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import Difficulty, GenerationJobStatus, QuestionType, QuizStatus


class QuizGenerateRequest(BaseModel):
    material_id: str | None = None
    material_ids: list[str] | None = None
    number_of_questions: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias=AliasChoices("number_of_questions", "question_count"),
    )
    difficulty: Difficulty = Difficulty.MEDIUM
    question_types: list[QuestionType] = Field(
        default_factory=lambda: [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
    )


class QuestionPublic(BaseModel):
    """Student-facing question shape used while taking a quiz: never includes the
    correct answer, explanation, or source reference."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    order_index: int
    question_type: QuestionType
    question_text: str
    options: list[str] | None
    difficulty: Difficulty
    topic: str


class QuestionWithAnswer(QuestionPublic):
    """Internal/review shape used after submission, or for scoring. Never returned
    from an endpoint that a student can hit before their attempt is submitted."""

    correct_answer: str
    explanation: str
    source_reference: str | None


from pydantic import BaseModel, ConfigDict, Field, computed_field

class QuizRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    material_id: str
    title: str
    difficulty: Difficulty
    number_of_questions: int
    status: QuizStatus
    generation_error: str | None
    created_at: datetime
    updated_at: datetime

    question_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def populate_question_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if ("question_count" not in data or not data["question_count"]) and data.get("questions"):
                data["question_count"] = len(data["questions"])
        elif hasattr(data, "questions") and getattr(data, "question_count", None) in (None, 0):
            try:
                qs = data.questions
                if qs:
                    setattr(data, "question_count", len(qs))
            except Exception:
                pass
        return data


class QuizDetail(QuizRead):
    questions: list[QuestionPublic]


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: GenerationJobStatus
    material_ids: list[str]
    question_count: int
    difficulty: Difficulty
    question_types: list[QuestionType]
    progress: int
    current_stage: str
    celery_task_id: str | None
    quiz_id: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
