from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.practice_generator import generate_practice_questions
from app.core.exceptions import ValidationFailedError
from app.models.answer import Answer
from app.models.attempt import QuizAttempt
from app.models.enums import Difficulty, QuestionType, QuizStatus
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.user import User
from app.models.weakness import Weakness
from app.services import material_service


def _material_topics(db: Session, *, material_id: str) -> set[str]:
    stmt = select(Question.topic).join(Quiz, Question.quiz_id == Quiz.id).where(Quiz.material_id == material_id)
    return set(db.scalars(stmt).all())


def _resolve_topics(db: Session, *, user_id: str, material_id: str, requested: list[str] | None) -> list[str]:
    if requested:
        return requested

    material_topics = _material_topics(db, material_id=material_id)
    weaknesses = list(
        db.scalars(
            select(Weakness)
            .where(Weakness.user_id == user_id, Weakness.topic.in_(material_topics))
            .order_by(Weakness.confidence.desc())
        ).all()
    )
    if not weaknesses:
        raise ValidationFailedError(
            "No weak topics found for this material yet, and none were specified. Attempt a "
            "quiz on this material first, or pass `topics` explicitly."
        )
    return [w.topic for w in weaknesses[:5]]


def _known_misconceptions(db: Session, *, user_id: str, material_id: str, topics: list[str]) -> str:
    stmt = (
        select(Answer.misconception, Question.topic)
        .join(Question, Answer.question_id == Question.id)
        .join(Quiz, Question.quiz_id == Quiz.id)
        .join(QuizAttempt, Answer.attempt_id == QuizAttempt.id)
        .where(
            QuizAttempt.user_id == user_id,
            Quiz.material_id == material_id,
            Question.topic.in_(topics),
            Answer.misconception.is_not(None),
        )
        .distinct()
        .limit(10)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return ""
    return "\n".join(f"- [{topic}] {misconception}" for misconception, topic in rows)


def _previously_asked(db: Session, *, material_id: str) -> str:
    stmt = select(Question.question_text).join(Quiz, Question.quiz_id == Quiz.id).where(
        Quiz.material_id == material_id
    ).limit(50)
    texts = db.scalars(stmt).all()
    return "\n".join(f"- {t}" for t in texts)


async def generate_practice(
    db: Session,
    *,
    user: User,
    material_id: str,
    number_of_questions: int,
    question_types: list[QuestionType],
    topics: list[str] | None,
) -> Quiz:
    material = material_service.get_owned_material(db, user=user, material_id=material_id)
    resolved_topics = _resolve_topics(db, user_id=user.id, material_id=material.id, requested=topics)

    quiz = Quiz(
        user_id=user.id,
        material_id=material.id,
        title=f"Targeted Practice: {', '.join(resolved_topics)}",
        difficulty=Difficulty.MEDIUM,
        status=QuizStatus.GENERATING,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    try:
        generated = await generate_practice_questions(
            db,
            user_id=user.id,
            material_id=material.id,
            number_of_questions=number_of_questions,
            question_types=question_types,
            weak_topics=resolved_topics,
            known_misconceptions=_known_misconceptions(
                db, user_id=user.id, material_id=material.id, topics=resolved_topics
            ),
            previously_asked=_previously_asked(db, material_id=material.id),
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
