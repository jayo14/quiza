from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.quiz_generator import generate_quiz_questions
from app.core.exceptions import NotFoundError, ValidationFailedError, safe_error_message
from app.models.enums import Difficulty, MaterialStatus, QuestionType, QuizStatus
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.user import User
from app.schemas.quiz import QuizRead
from app.services import material_service


async def generate_quiz(
    db: Session,
    *,
    user: User,
    material_id: str | None = None,
    material_ids: list[str] | None = None,
    number_of_questions: int = 5,
    difficulty: Difficulty = Difficulty.MEDIUM,
    question_types: list[QuestionType] | None = None,
) -> Quiz:
    target_ids = list(set(filter(None, (material_ids or []) + ([material_id] if material_id else []))))
    if not target_ids:
        raise ValidationFailedError("At least one material_id must be provided for quiz generation.")

    materials = [material_service.get_owned_material(db, user=user, material_id=mid) for mid in target_ids]
    failed = [m for m in materials if m.status == MaterialStatus.FAILED]
    if failed:
        details = ", ".join(f"{m.filename} ({m.processing_error or 'Processing failed'})" for m in failed)
        raise ValidationFailedError(
            f"Study material processing failed: {details}. Please retry uploading or choose another file."
        )

    unready = [m.filename for m in materials if m.status != MaterialStatus.READY]
    if unready:
        raise ValidationFailedError(
            f"Study material is still processing: {', '.join(unready)}. Please wait for ingestion to finish."
        )

    # Use the user's requested count directly (validated 1-50 by schema).
    effective_count = number_of_questions
    primary_material = materials[0]
    title = f"Quiz: {primary_material.title}" if len(materials) == 1 else f"Multi-Material Quiz ({len(materials)} sources)"

    quiz = Quiz(
        user_id=user.id,
        material_id=primary_material.id,
        title=title,
        difficulty=difficulty,
        number_of_questions=effective_count,
        status=QuizStatus.GENERATING,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    q_types = question_types or [QuestionType.MULTIPLE_CHOICE]

    try:
        # If multiple materials, search vector store across primary material (or iterate context)
        generated = await generate_quiz_questions(
            db,
            user_id=user.id,
            material_id=primary_material.id,
            material_ids=target_ids,
            number_of_questions=effective_count,
            difficulty=difficulty,
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
        db.refresh(quiz)
        return quiz
    except Exception as exc:
        db.rollback()
        quiz.status = QuizStatus.FAILED
        quiz.generation_error = safe_error_message(exc)
        db.add(quiz)
        try:
            db.commit()
        except Exception:
            db.rollback()
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = safe_error_message(exc)
            db.add(quiz)
            db.commit()
        raise


def list_quizzes(db: Session, *, user: User) -> list[Quiz]:
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.user_id == user.id)
        .order_by(Quiz.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_owned_quiz(db: Session, *, user: User, quiz_id: str) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != user.id:
        raise NotFoundError("Quiz not found.")
    return quiz


def delete_quiz(db: Session, *, user: User, quiz_id: str) -> None:
    quiz = get_owned_quiz(db, user=user, quiz_id=quiz_id)
    db.delete(quiz)
    db.commit()
