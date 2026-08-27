from datetime import datetime

from pydantic import BaseModel


class SummaryContentRead(BaseModel):
    overall_performance: str
    understood_topics: list[str]
    struggled_topics: list[str]
    key_mistakes: list[str]
    weak_topics: list[str]
    concept_explanations: list[str]
    recommended_revision: list[str]
    recommended_practice: list[str]
    progress_note: str


class SummaryRead(BaseModel):
    id: str
    attempt_id: str
    content: SummaryContentRead
    created_at: datetime
