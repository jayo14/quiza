from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, QuestionType, QuizStatus


class QuizGenerateRequest(BaseModel):
    material_id: str
    number_of_questions: int = Field(default=10, ge=1, le=50)
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


class QuizRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    material_id: str
    title: str
    difficulty: Difficulty
    status: QuizStatus
    generation_error: str | None
    created_at: datetime
    updated_at: datetime


class QuizDetail(QuizRead):
    questions: list[QuestionPublic]
