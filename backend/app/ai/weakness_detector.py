from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.attempt import QuizAttempt
from app.models.enums import AttemptStatus, Severity
from app.models.question import Question
from app.models.weakness import Weakness

# A weakness is declared once at least 2 questions are answered on a topic below accuracy threshold.
MIN_QUESTIONS_FOR_WEAKNESS = 2
WEAKNESS_ACCURACY_THRESHOLD = 0.6
HIGH_SEVERITY_ACCURACY = 0.4


@dataclass(frozen=True)
class TopicStats:
    topic: str
    question_count: int
    mistake_count: int
    attempt_count: int
    accuracy: float


def compute_topic_stats(db: Session, *, user_id: str, topics: set[str]) -> list[TopicStats]:
    if not topics:
        return []

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
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == AttemptStatus.COMPLETED,
            Question.topic.in_(topics),
        )
        .group_by(Question.topic)
    ).all()

    stats = []
    for topic, question_count, mistake_count, attempt_count in rows:
        mistake_count = mistake_count or 0
        accuracy = (question_count - mistake_count) / question_count if question_count else 0.0
        stats.append(
            TopicStats(
                topic=topic,
                question_count=question_count,
                mistake_count=mistake_count,
                attempt_count=attempt_count,
                accuracy=accuracy,
            )
        )
    return stats


def detect_and_update_weaknesses(db: Session, *, user_id: str, topics: set[str]) -> list[Weakness]:
    """Recomputes weakness status for the given topics from scratch, across all of
    the user's completed attempts. Creates/updates a Weakness row while a topic
    stays below the accuracy threshold with enough evidence, and removes it once
    the student's accuracy on that topic recovers — so `Weakness` rows always
    reflect current standing, not history."""

    stats = compute_topic_stats(db, user_id=user_id, topics=topics)
    stats_by_topic = {s.topic: s for s in stats}

    existing_rows = db.scalars(
        select(Weakness).where(Weakness.user_id == user_id, Weakness.topic.in_(topics))
    ).all()
    existing_by_topic = {row.topic: row for row in existing_rows}

    updated: list[Weakness] = []
    for topic in topics:
        stat = stats_by_topic.get(topic)
        existing = existing_by_topic.get(topic)

        is_weak = (
            stat is not None
            and stat.question_count >= MIN_QUESTIONS_FOR_WEAKNESS
            and stat.accuracy < WEAKNESS_ACCURACY_THRESHOLD
        )

        if not is_weak:
            if existing:
                db.delete(existing)
            continue

        confidence = min(1.0, stat.question_count / 10) * (1 - stat.accuracy)
        severity = Severity.HIGH if stat.accuracy < HIGH_SEVERITY_ACCURACY else Severity.MEDIUM

        row = existing or Weakness(user_id=user_id, topic=topic, concept="")
        row.attempt_count = stat.attempt_count
        row.question_count = stat.question_count
        row.mistake_count = stat.mistake_count
        row.accuracy = stat.accuracy
        row.confidence = confidence
        row.severity = severity
        row.last_seen = datetime.now(timezone.utc)
        db.add(row)
        updated.append(row)

    db.commit()
    return updated
