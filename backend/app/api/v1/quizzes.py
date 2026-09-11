from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import enforce_ai_rate_limit
from app.models.user import User
from app.schemas.attempt import AttemptRead
from app.schemas.quiz import QuestionPublic, QuizDetail, QuizGenerateRequest, QuizRead
from app.services import attempt_service, quiz_service

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


async def _run_background_quiz_generation(
    quiz_id: str,
    user_id: str,
    material_ids: list[str],
    number_of_questions: int,
    difficulty: str,
    question_types: list[str],
) -> None:
    """Background task: ingest unfinished materials, then generate quiz questions."""
    import logging
    from app.db.session import SessionLocal
    from app.models.material import Material
    from app.models.enums import MaterialStatus, QuizStatus, Difficulty, QuestionType
    from app.models.question import Question
    from app.models.quiz import Quiz
    from app.ai.rag.ingestion import run_ingestion_for_material
    from app.ai.quiz_generator import generate_quiz_questions

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    try:
        quiz = db.get(Quiz, quiz_id)
        if not quiz:
            return

        # Step 1: Ingest any materials that aren't ready yet
        for mid in material_ids:
            mat = db.get(Material, mid)
            if mat and mat.status == MaterialStatus.UPLOADED:
                logger.info("Ingesting material %s before quiz generation...", mat.filename)
                try:
                    await run_ingestion_for_material(mat.id)
                except Exception as e:
                    logger.error("Ingestion failed for %s: %s", mat.filename, e)

        # Step 2: Refresh materials to check status
        materials = [db.get(Material, mid) for mid in material_ids]
        materials = [m for m in materials if m]

        failed = [m for m in materials if m.status == MaterialStatus.FAILED]
        if failed:
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = f"Ingestion failed for: {', '.join(m.filename for m in failed)}"
            db.add(quiz)
            db.commit()
            return

        unready = [m for m in materials if m.status != MaterialStatus.READY]
        if unready:
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = f"Materials still processing: {', '.join(m.filename for m in unready)}"
            db.add(quiz)
            db.commit()
            return

        # Step 3: Generate quiz questions
        primary = materials[0]
        diff = Difficulty(difficulty)
        q_types = [QuestionType(t) for t in question_types]

        generated = await generate_quiz_questions(
            db,
            user_id=user_id,
            material_id=primary.id,
            number_of_questions=number_of_questions,
            difficulty=diff,
            question_types=q_types,
        )

        db.add_all(
            [
                Question(
                    quiz_id=quiz.id,
                    order_index=i,
                    question_type=q.question_type,
                    question_text=q.question,
                    options=q.options,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    source_reference=q.source_reference,
                )
                for i, q in enumerate(generated)
            ]
        )
        quiz.status = QuizStatus.READY
        quiz.generation_error = None
        db.add(quiz)
        db.commit()
        logger.info("Background quiz %s generated %d questions.", quiz_id, len(generated))

    except Exception as exc:
        logger.exception("Background quiz generation failed for %s", quiz_id)
        try:
            quiz = db.get(Quiz, quiz_id)
            if quiz:
                quiz.status = QuizStatus.FAILED
                quiz.generation_error = str(exc)[:1000]
                db.add(quiz)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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
        material_ids=payload.material_ids,
        number_of_questions=payload.number_of_questions,
        difficulty=payload.difficulty,
        question_types=payload.question_types,
    )
    return QuizDetail.model_validate(quiz)


@router.post(
    "/generate-background", response_model=QuizRead, status_code=202,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
async def generate_quiz_background(
    payload: QuizGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizRead:
    """Queue quiz generation as a background task. Returns immediately.

    Materials that aren't ingested yet will be ingested first, then quiz
    questions are generated. Poll GET /quizzes/{id} to check completion.
    """
    from fastapi import HTTPException
    from app.services import material_service
    from app.models.enums import QuizStatus
    from app.models.quiz import Quiz

    target_ids = list(set(filter(None, (payload.material_ids or []) + ([payload.material_id] if payload.material_id else []))))
    if not target_ids:
        raise HTTPException(status_code=400, detail="At least one material_id is required.")

    materials = [material_service.get_owned_material(db, user=current_user, material_id=mid) for mid in target_ids]
    primary = materials[0]
    title = f"Quiz: {primary.title}" if len(materials) == 1 else f"Multi-Material Quiz ({len(materials)} sources)"

    quiz = Quiz(
        user_id=current_user.id,
        material_id=primary.id,
        title=title,
        difficulty=payload.difficulty,
        status=QuizStatus.GENERATING,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    background_tasks.add_task(
        _run_background_quiz_generation,
        quiz_id=quiz.id,
        user_id=current_user.id,
        material_ids=target_ids,
        number_of_questions=payload.number_of_questions,
        difficulty=payload.difficulty.value,
        question_types=[t.value for t in payload.question_types],
    )

    return QuizRead.model_validate(quiz)


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
