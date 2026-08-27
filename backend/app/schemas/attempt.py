from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AttemptStatus


class AnswerSubmit(BaseModel):
    question_id: str
    selected_answer: str | None = None
    time_taken_seconds: float | None = None


class SubmitAttemptRequest(BaseModel):
    answers: list[AnswerSubmit]


class AnswerResult(BaseModel):
    question_id: str
    question_text: str
    topic: str
    selected_answer: str | None
    correct_answer: str
    explanation: str
    is_correct: bool | None
    time_taken_seconds: float | None


class TopicPerformance(BaseModel):
    topic: str
    total: int
    correct: int
    accuracy: float


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quiz_id: str
    status: AttemptStatus
    started_at: datetime | None
    submitted_at: datetime | None
    total_questions: int
    correct_count: int
    incorrect_count: int
    score: float | None
    accuracy: float | None
    created_at: datetime


class AttemptResult(AttemptRead):
    answers: list[AnswerResult]
    topic_performance: list[TopicPerformance]
