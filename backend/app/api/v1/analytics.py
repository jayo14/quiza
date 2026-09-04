from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import TopicMasteryRead, WeaknessRead
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/weaknesses", response_model=list[WeaknessRead])
def list_weaknesses(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WeaknessRead]:
    return analytics_service.list_weaknesses(db, user=current_user)


@router.get("/topics", response_model=list[TopicMasteryRead])
def get_topic_mastery(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TopicMasteryRead]:
    return analytics_service.get_topic_mastery(db, user=current_user)
