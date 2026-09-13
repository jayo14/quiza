from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import QuizStatus
from app.models.quiz import Quiz
from app.models.user import User


def list_quizzes(db: Session, *, user: User) -> list[Quiz]:
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.user_id == user.id, Quiz.status != QuizStatus.FAILED)
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
