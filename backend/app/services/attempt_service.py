from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.weakness_detector import detect_and_update_weaknesses
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.models.answer import Answer
from app.models.enums import AttemptStatus, QuestionType, QuizStatus
from app.models.attempt import QuizAttempt
from app.models.question import Question
from app.models.user import User
from app.schemas.attempt import AnswerResult, AnswerSubmit, TopicPerformance
from app.services import quiz_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_attempt(db: Session, *, user: User, quiz_id: str) -> QuizAttempt:
    quiz = quiz_service.get_owned_quiz(db, user=user, quiz_id=quiz_id)
    if quiz.status not in (QuizStatus.READY,):
        raise ValidationFailedError("This quiz isn't ready to be attempted yet.")

    existing = db.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user.id,
            QuizAttempt.status == AttemptStatus.IN_PROGRESS,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if existing:
        return existing

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=_now(),
        total_questions=len(quiz.questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def get_owned_attempt(db: Session, *, user: User, attempt_id: str) -> QuizAttempt:
    attempt = db.get(QuizAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise NotFoundError("Attempt not found.")
    return attempt


def list_attempts(db: Session, *, user: User) -> list[QuizAttempt]:
    stmt = select(QuizAttempt).where(QuizAttempt.user_id == user.id).order_by(QuizAttempt.created_at.desc())
    return list(db.scalars(stmt).all())


def _is_correct(question: Question, selected_answer: str | None) -> bool:
    if selected_answer is None:
        return False
    if question.question_type in (QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE, QuestionType.SHORT_ANSWER):
        return selected_answer.strip().lower() == question.correct_answer.strip().lower()
    return False


def submit_attempt(
    db: Session, *, user: User, attempt_id: str, submissions: list[AnswerSubmit]
) -> QuizAttempt:
    attempt = db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user.id)
        .with_for_update()
    ).scalar_one_or_none()
    if not attempt:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Attempt not found.")
    if attempt.status == AttemptStatus.COMPLETED:
        raise ValidationFailedError("This attempt has already been submitted.")

    quiz = quiz_service.get_owned_quiz(db, user=user, quiz_id=attempt.quiz_id)
    submission_by_question = {s.question_id: s for s in submissions}

    correct_count = 0
    answer_rows: list[Answer] = []
    for question in quiz.questions:
        submission = submission_by_question.get(question.id)
        selected_answer = submission.selected_answer if submission else None
        correct = _is_correct(question, selected_answer)
        if correct:
            correct_count += 1
        answer_rows.append(
            Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_answer=selected_answer,
                is_correct=correct,
                time_taken_seconds=submission.time_taken_seconds if submission else None,
                submitted_at=_now(),
            )
        )

    db.add_all(answer_rows)

    total = len(quiz.questions)
    attempt.correct_count = correct_count
    attempt.incorrect_count = total - correct_count
    attempt.score = float(correct_count)
    attempt.accuracy = (correct_count / total) if total else 0.0
    attempt.status = AttemptStatus.COMPLETED
    attempt.submitted_at = _now()
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Deterministic, no LLM involved: cheap enough to run inline on every
    # submission so weakness data is always current by the time the response
    # (and later, the summary/practice endpoints) are read.
    topics = {q.topic for q in quiz.questions}
    detect_and_update_weaknesses(db, user_id=user.id, topics=topics)

    return attempt


def build_answer_results(db: Session, attempt: QuizAttempt) -> list[AnswerResult]:
    if attempt.status != AttemptStatus.COMPLETED:
        return []

    questions_by_id = {q.id: q for q in attempt.quiz.questions}
    results = []
    for answer in attempt.answers:
        question = questions_by_id[answer.question_id]
        results.append(
            AnswerResult(
                question_id=question.id,
                question_text=question.question_text,
                topic=question.topic,
                selected_answer=answer.selected_answer,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                is_correct=answer.is_correct,
                time_taken_seconds=answer.time_taken_seconds,
            )
        )
    return results


def build_topic_performance(db: Session, attempt: QuizAttempt) -> list[TopicPerformance]:
    if attempt.status != AttemptStatus.COMPLETED:
        return []

    questions_by_id = {q.id: q for q in attempt.quiz.questions}
    totals: dict[str, int] = defaultdict(int)
    corrects: dict[str, int] = defaultdict(int)

    for answer in attempt.answers:
        topic = questions_by_id[answer.question_id].topic
        totals[topic] += 1
        if answer.is_correct:
            corrects[topic] += 1

    return [
        TopicPerformance(topic=topic, total=total, correct=corrects[topic], accuracy=corrects[topic] / total)
        for topic, total in totals.items()
    ]
