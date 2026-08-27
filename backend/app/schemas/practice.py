from pydantic import BaseModel, Field

from app.models.enums import QuestionType


class PracticeGenerateRequest(BaseModel):
    material_id: str
    number_of_questions: int = Field(default=5, ge=1, le=20)
    question_types: list[QuestionType] = Field(
        default_factory=lambda: [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
    )
    # Optional explicit topic focus; when omitted, the student's current weak topics
    # (that overlap with this material) are used automatically.
    topics: list[str] | None = None
