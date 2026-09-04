from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.attempt import QuizAttempt
from app.models.enums import AttemptStatus
from app.models.question import Question
from app.models.user import User
from app.models.weakness import Weakness
from app.schemas.analytics import TopicMasteryRead


def list_weaknesses(db: Session, *, user: User) -> list[Weakness]:
    stmt = (
        select(Weakness)
        .where(Weakness.user_id == user.id)
        .order_by(Weakness.confidence.desc(), Weakness.accuracy.asc())
    )
    return list(db.scalars(stmt).all())


def get_topic_mastery(db: Session, *, user: User) -> list[TopicMasteryRead]:
    rows = db.execute(
        select(
            Question.topic,
            func.count(Answer.id),
            func.sum(case((Answer.is_correct == False, 1), else_=0)),  # noqa: E712
            func.count(func.distinct(Answer.attempt_id)),
        )
        .join(Question, Answer.question_id == Question.id)
        .join(QuizAttempt, Answer.attempt_id == QuizAttempt.id)
        .where(
            QuizAttempt.user_id == user.id,
            QuizAttempt.status == AttemptStatus.COMPLETED,
        )
        .group_by(Question.topic)
        .order_by(Question.topic.asc())
    ).all()

    mastery_list: list[TopicMasteryRead] = []
    for topic, question_count, mistake_count, attempt_count in rows:
        mistakes = mistake_count or 0
        accuracy = (question_count - mistakes) / question_count if question_count else 0.0
        if accuracy >= 0.8:
            status = "Mastered"
        elif accuracy >= 0.6:
            status = "Developing"
        else:
            status = "Needs Focus"

        mastery_list.append(
            TopicMasteryRead(
                topic=topic,
                question_count=question_count,
                mistake_count=mistakes,
                attempt_count=attempt_count,
                accuracy=accuracy,
                status=status,
            )
        )
    return mastery_list
