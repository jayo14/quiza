from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import enforce_ai_rate_limit
from app.models.user import User
from app.schemas.practice import PracticeGenerateRequest
from app.schemas.quiz import QuizDetail
from app.services import practice_service

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post(
    "/generate", response_model=QuizDetail, status_code=201, dependencies=[Depends(enforce_ai_rate_limit)]
)
async def generate_practice(
    payload: PracticeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizDetail:
    quiz = await practice_service.generate_practice(
        db,
        user=current_user,
        material_id=payload.material_id,
        number_of_questions=payload.number_of_questions,
        question_types=payload.question_types,
        topics=payload.topics,
    )
    return QuizDetail.model_validate(quiz)
