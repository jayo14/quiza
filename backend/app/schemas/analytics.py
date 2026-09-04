from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Severity


class WeaknessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    topic: str
    concept: str
    attempt_count: int
    question_count: int
    mistake_count: int
    accuracy: float
    confidence: float
    severity: Severity
    last_seen: datetime | None


class TopicMasteryRead(BaseModel):
    topic: str
    question_count: int
    mistake_count: int
    attempt_count: int
    accuracy: float
    status: str
