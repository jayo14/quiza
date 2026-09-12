import json

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMProvider
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.summary import SUMMARY_SYSTEM_PROMPT, build_summary_user_prompt
from app.models.attempt import QuizAttempt
from app.models.enums import AttemptStatus
from app.models.weakness import Weakness
from app.services import attempt_service


class SummaryContent(BaseModel):
    overall_performance: str = Field(description="1-2 sentence summary of how the attempt went.")
    understood_topics: list[str] = Field(default_factory=list)
    struggled_topics: list[str] = Field(default_factory=list)
    key_mistakes: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
    concept_explanations: list[str] = Field(default_factory=list)
    recommended_revision: list[str] = Field(default_factory=list)
    recommended_practice: list[str] = Field(default_factory=list)
    progress_note: str = Field(description="How this attempt compares to previous ones, or a note that there's no prior data.")


def _format_topic_performance(topic_performance) -> str:
    if not topic_performance:
        return "(no per-topic data)"
    return "\n".join(f"- {t.topic}: {t.correct}/{t.total} ({t.accuracy:.0%})" for t in topic_performance)


def _format_missed_questions(answer_results) -> str:
    missed = [a for a in answer_results if not a.is_correct]
    if not missed:
        return "(none — all questions correct)"
    lines = []
    for a in missed:
        lines.append(f"- [{a.topic}] {a.question_text} | student answered: {a.selected_answer!r}")
    return "\n".join(lines)


def _format_weaknesses(weaknesses: list[Weakness]) -> str:
    if not weaknesses:
        return "(no established weak topics yet)"
    return "\n".join(
        f"- {w.topic}: {w.accuracy:.0%} accuracy over {w.question_count} questions "
        f"(confidence {w.confidence:.0%}, severity {w.severity.value})"
        for w in weaknesses
    )


def _format_previous_comparison(current: QuizAttempt, previous: list[QuizAttempt]) -> str:
    if not previous:
        return "This is the student's first completed attempt on this material."
    last = previous[0]
    delta = (current.accuracy or 0) - (last.accuracy or 0)
    direction = "improved" if delta > 0 else "declined" if delta < 0 else "stayed the same"
    return (
        f"Previous attempt accuracy: {last.accuracy:.0%}. Current: {(current.accuracy or 0):.0%}. "
        f"Accuracy has {direction} ({delta:+.0%})."
    )


async def generate_attempt_summary(
    db: Session, *, attempt: QuizAttempt, llm: LLMProvider | None = None
) -> tuple[str, SummaryContent]:
    from app.core.exceptions import ValidationFailedError

    if attempt.status != AttemptStatus.COMPLETED:
        raise ValidationFailedError("Cannot summarize an attempt that hasn't been submitted yet.")

    answer_results = attempt_service.build_answer_results(db, attempt)
    topic_performance = attempt_service.build_topic_performance(db, attempt)

    weaknesses = list(
        db.scalars(select(Weakness).where(Weakness.user_id == attempt.user_id)).all()
    )

    previous_attempts = list(
        db.scalars(
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == attempt.user_id,
                QuizAttempt.quiz_id == attempt.quiz_id,
                QuizAttempt.status == AttemptStatus.COMPLETED,
                QuizAttempt.id != attempt.id,
            )
            .order_by(QuizAttempt.submitted_at.desc())
        ).all()
    )

    provider = llm or get_llm_provider()
    schema_hint = json.dumps(SummaryContent.model_json_schema(), indent=2)
    full_system_prompt = (
        f"{SUMMARY_SYSTEM_PROMPT}\n\n"
        "Respond with ONLY a single JSON object (no markdown fences, no prose) "
        f"that matches this JSON schema:\n{schema_hint}"
    )
    user_prompt = build_summary_user_prompt(
        quiz_title=attempt.quiz.title,
        score=attempt.score or 0,
        accuracy=attempt.accuracy or 0,
        total_questions=attempt.total_questions,
        correct_count=attempt.correct_count,
        incorrect_count=attempt.incorrect_count,
        topic_performance=_format_topic_performance(topic_performance),
        missed_questions=_format_missed_questions(answer_results),
        known_weaknesses=_format_weaknesses(weaknesses),
        previous_attempt_comparison=_format_previous_comparison(attempt, previous_attempts),
    )
    content = await provider.generate_structured(
        system_prompt=full_system_prompt,
        user_prompt=user_prompt,
        response_model=SummaryContent,
    )
    return content.model_dump_json(), content
