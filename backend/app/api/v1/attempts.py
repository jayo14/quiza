from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.ai.answer_analyzer import analyze_attempt_mistakes
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.attempt import AttemptRead, AttemptResult, SubmitAttemptRequest
from app.services import attempt_service

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _to_result(db: Session, attempt) -> AttemptResult:
    return AttemptResult(
        **AttemptRead.model_validate(attempt).model_dump(),
        answers=attempt_service.build_answer_results(db, attempt),
        topic_performance=attempt_service.build_topic_performance(db, attempt),
    )


@router.post("/{attempt_id}/submit", response_model=AttemptResult)
def submit_attempt(
    attempt_id: str,
    payload: SubmitAttemptRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptResult:
    attempt = attempt_service.submit_attempt(
        db, user=current_user, attempt_id=attempt_id, submissions=payload.answers
    )
    # Scoring, topic performance, and deterministic weakness detection are already
    # done synchronously above. The LLM-driven per-mistake diagnosis is comparatively
    # slow and not needed for the immediate result screen, so it runs after response.
    background_tasks.add_task(analyze_attempt_mistakes, attempt.id)
    return _to_result(db, attempt)


@router.get("/{attempt_id}", response_model=AttemptResult)
def get_attempt(
    attempt_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AttemptResult:
    attempt = attempt_service.get_owned_attempt(db, user=current_user, attempt_id=attempt_id)
    return _to_result(db, attempt)


@router.get("", response_model=list[AttemptRead])
def list_attempts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AttemptRead]:
    return attempt_service.list_attempts(db, user=current_user)
