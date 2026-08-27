from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import enforce_ai_rate_limit
from app.models.user import User
from app.schemas.attempt import AttemptRead
from app.schemas.quiz import QuestionPublic, QuizDetail, QuizGenerateRequest, QuizRead
from app.services import attempt_service, quiz_service

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post(
    "/generate", response_model=QuizDetail, status_code=201, dependencies=[Depends(enforce_ai_rate_limit)]
)
async def generate_quiz(
    payload: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizDetail:
    quiz = await quiz_service.generate_quiz(
        db,
        user=current_user,
        material_id=payload.material_id,
        number_of_questions=payload.number_of_questions,
        difficulty=payload.difficulty,
        question_types=payload.question_types,
    )
    return QuizDetail.model_validate(quiz)


@router.get("", response_model=list[QuizRead])
def list_quizzes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[QuizRead]:
    return quiz_service.list_quizzes(db, user=current_user)


@router.get("/{quiz_id}", response_model=QuizRead)
def get_quiz(quiz_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> QuizRead:
    return quiz_service.get_owned_quiz(db, user=current_user, quiz_id=quiz_id)


@router.get("/{quiz_id}/questions", response_model=list[QuestionPublic])
def get_quiz_questions(
    quiz_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[QuestionPublic]:
    quiz = quiz_service.get_owned_quiz(db, user=current_user, quiz_id=quiz_id)
    return quiz.questions


@router.delete("/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    quiz_service.delete_quiz(db, user=current_user, quiz_id=quiz_id)


@router.post("/{quiz_id}/attempts", response_model=AttemptRead, status_code=201)
def start_attempt(
    quiz_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AttemptRead:
    return attempt_service.start_attempt(db, user=current_user, quiz_id=quiz_id)
