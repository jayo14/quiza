from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import enforce_ai_rate_limit
from app.models.user import User
from app.schemas.attempt import AttemptRead
from app.schemas.quiz import (
    GenerationJobRead,
    QuestionPublic,
    QuizGenerateRequest,
    QuizRead,
)
from app.services import attempt_service, quiz_service

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post(
    "/generate-background", response_model=GenerationJobRead, status_code=202,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
async def generate_quiz_background(
    payload: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerationJobRead:
    """Queue quiz generation as a Celery task. Returns immediately.

    Materials are ingested by the worker only when this job is processed.
    """
    from fastapi import HTTPException
    from app.services import material_service
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus
    from app.tasks import generate_quiz_task

    target_ids = list(dict.fromkeys(
        filter(None, (payload.material_ids or []) + ([payload.material_id] if payload.material_id else []))
    ))
    if not target_ids:
        raise HTTPException(status_code=400, detail="At least one material_id is required.")

    for material_id in target_ids:
        material_service.get_owned_material(db, user=current_user, material_id=material_id)

    job = GenerationJob(
        user_id=current_user.id,
        status=GenerationJobStatus.QUEUED,
        material_ids=target_ids,
        question_count=payload.number_of_questions,
        difficulty=payload.difficulty.value,
        question_types=[question_type.value for question_type in payload.question_types],
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        task_result = generate_quiz_task.delay(
            job_id=job.id,
            user_id=current_user.id,
            material_ids=target_ids,
            question_count=payload.number_of_questions,
            difficulty=payload.difficulty.value,
            question_types=[t.value for t in payload.question_types],
        )
        job.celery_task_id = task_result.id
        db.commit()
        db.refresh(job)
    except Exception as exc:
        job.status = GenerationJobStatus.FAILED
        job.error_message = "The quiz generation worker could not be reached."
        db.commit()
        raise HTTPException(status_code=503, detail=job.error_message) from exc

    return GenerationJobRead.model_validate(job)


@router.get("/generation-jobs", response_model=list[GenerationJobRead])
def list_generation_jobs(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[GenerationJobRead]:
    from sqlalchemy import select
    from app.models.generation_job import GenerationJob

    jobs = db.scalars(
        select(GenerationJob)
        .where(GenerationJob.user_id == current_user.id)
        .order_by(GenerationJob.created_at.desc())
    ).all()
    return [GenerationJobRead.model_validate(job) for job in jobs]


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobRead)
def get_generation_job(
    job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GenerationJobRead:
    from app.models.generation_job import GenerationJob
    from app.core.exceptions import NotFoundError

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError("Generation job not found.")
    return GenerationJobRead.model_validate(job)


@router.post(
    "/generation-jobs/{job_id}/retry", response_model=GenerationJobRead, status_code=202,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def retry_generation_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerationJobRead:
    from fastapi import HTTPException
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus
    from app.core.exceptions import NotFoundError
    from app.tasks import generate_quiz_task

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError("Generation job not found.")

    job.status = GenerationJobStatus.QUEUED
    job.progress = 0
    job.current_stage = "queued"
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)

    try:
        task_result = generate_quiz_task.delay(
            job_id=job.id,
            user_id=current_user.id,
            material_ids=job.material_ids,
            question_count=job.question_count,
            difficulty=job.difficulty,
            question_types=job.question_types,
        )
        job.celery_task_id = task_result.id
        db.commit()
        db.refresh(job)
    except Exception as exc:
        job.status = GenerationJobStatus.FAILED
        job.error_message = "The quiz generation worker could not be reached."
        db.commit()
        raise HTTPException(status_code=503, detail=job.error_message) from exc

    return GenerationJobRead.model_validate(job)


@router.post(
    "/generation-jobs/{job_id}/cancel", response_model=GenerationJobRead, status_code=200,
)
def cancel_generation_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerationJobRead:
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus
    from app.core.exceptions import NotFoundError
    from app.core.celery_app import celery_app

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError("Generation job not found.")

    if job.status not in (GenerationJobStatus.QUEUED, GenerationJobStatus.PROCESSING):
        raise HTTPException(status_code=400, detail="Job is not active and cannot be cancelled.")

    if job.celery_task_id:
        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")

    job.status = GenerationJobStatus.CANCELLED
    job.current_stage = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = None
    db.add(job)
    db.commit()
    db.refresh(job)

    return GenerationJobRead.model_validate(job)


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
