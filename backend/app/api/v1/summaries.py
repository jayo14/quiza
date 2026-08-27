from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import enforce_ai_rate_limit
from app.models.user import User
from app.schemas.summary import SummaryRead
from app.services import summary_service

router = APIRouter(prefix="/attempts", tags=["summaries"])


@router.get(
    "/{attempt_id}/summary", response_model=SummaryRead, dependencies=[Depends(enforce_ai_rate_limit)]
)
async def get_attempt_summary(
    attempt_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SummaryRead:
    summary = await summary_service.get_or_generate_summary(db, user=current_user, attempt_id=attempt_id)
    return SummaryRead(
        id=summary.id, attempt_id=summary.attempt_id, content=summary.content, created_at=summary.created_at
    )
