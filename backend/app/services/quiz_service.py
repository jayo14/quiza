from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.quiz_generator import generate_quiz_questions
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.models.enums import Difficulty, MaterialStatus, QuestionType, QuizStatus
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.user import User
from app.services import material_service


async def generate_quiz(
    db: Session,
    *,
    user: User,
    material_id: str,
    number_of_questions: int,
    difficulty: Difficulty,
    question_types: list[QuestionType],
) -> Quiz:
    material = material_service.get_owned_material(db, user=user, material_id=material_id)
    if material.status != MaterialStatus.READY:
        raise ValidationFailedError(
            f"Material is not ready for quiz generation yet (status: {material.status.value})."
        )

    quiz = Quiz(
        user_id=user.id,
        material_id=material.id,
        title=f"Quiz: {material.title}",
        difficulty=difficulty,
        status=QuizStatus.GENERATING,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    try:
        generated = await generate_quiz_questions(
            db,
            user_id=user.id,
            material_id=material.id,
            number_of_questions=number_of_questions,
            difficulty=difficulty,
            question_types=question_types,
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
        quiz.generation_error = str(exc)
        db.add(quiz)
        db.commit()
        raise


def list_quizzes(db: Session, *, user: User) -> list[Quiz]:
    stmt = select(Quiz).where(Quiz.user_id == user.id).order_by(Quiz.created_at.desc())
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
