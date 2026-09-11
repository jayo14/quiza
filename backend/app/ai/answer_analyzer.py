import logging

from pydantic import BaseModel
from sqlalchemy import func, select

from app.ai.llm.base import LLMProvider
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.mistake_analysis import (
    MISTAKE_ANALYSIS_SYSTEM_PROMPT,
    build_mistake_analysis_user_prompt,
)
from app.ai.rag.pipeline import get_context_for_query
from app.core.exceptions import AIServiceError
from app.db.session import SessionLocal
from app.models.answer import Answer
from app.models.attempt import QuizAttempt
from app.models.enums import ErrorType, RecommendedAction, Severity

logger = logging.getLogger(__name__)


class MistakeAnalysisResult(BaseModel):
    error_type: ErrorType
    concept: str
    explanation: str
    misconception: str
    severity: Severity
    recommended_action: RecommendedAction


async def analyze_mistake(
    *,
    question_text: str,
    correct_answer: str,
    student_answer: str,
    topic: str,
    context: str,
    previous_mistake_count: int,
    llm: LLMProvider | None = None,
) -> MistakeAnalysisResult:
    """Runs one question/answer pair through the LLM to produce a structured mistake
    diagnosis. Raises AIServiceError (via LLMProvider.generate_structured) on
    failure — callers run this per-answer in a loop and must catch that themselves
    so one bad diagnosis doesn't drop the rest."""

    provider = llm or get_llm_provider()
    return await provider.generate_structured(
        system_prompt=MISTAKE_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=build_mistake_analysis_user_prompt(
            question_text=question_text,
            correct_answer=correct_answer,
            student_answer=student_answer,
            topic=topic,
            context=context,
            previous_mistake_count=previous_mistake_count,
        ),
        response_model=MistakeAnalysisResult,
    )


async def analyze_attempt_mistakes(attempt_id: str) -> None:
    """Background-task entry point: diagnoses every incorrect answer on a completed
    attempt and writes the structured result back onto the Answer row. Owns its own
    DB session since it runs after the submitting request has already returned.
    Each answer is analyzed independently and a failure on one never stops the
    rest — mistake analysis is a value-add, not something that can take the
    attempt-submission flow down with it."""

    db = SessionLocal()
    try:
        attempt = db.get(QuizAttempt, attempt_id)
        if attempt is None:
            logger.warning("analyze_attempt_mistakes: attempt %s not found", attempt_id)
            return

        incorrect_answers = db.scalars(
            select(Answer).where(Answer.attempt_id == attempt_id, Answer.is_correct == False)  # noqa: E712
        ).all()
        if not incorrect_answers:
            return

        quiz = attempt.quiz
        questions_by_id = {q.id: q for q in quiz.questions}

        for answer in incorrect_answers:
            question = questions_by_id.get(answer.question_id)
            if question is None or not answer.selected_answer:
                continue

            previous_mistake_count = db.scalar(
                select(func.count(Answer.id))
                .join(QuizAttempt, Answer.attempt_id == QuizAttempt.id)
                .where(
                    QuizAttempt.user_id == attempt.user_id,
                    Answer.question_id == answer.question_id,
                    Answer.is_correct == False,  # noqa: E712
                    Answer.id != answer.id,
                )
            ) or 0

            try:
                context = await get_context_for_query(
                    db,
                    user_id=attempt.user_id,
                    query=question.question_text,
                    material_id=quiz.material_id,
                    top_k=3,
                )
                result = await analyze_mistake(
                    question_text=question.question_text,
                    correct_answer=question.correct_answer,
                    student_answer=answer.selected_answer,
                    topic=question.topic,
                    context=context.text,
                    previous_mistake_count=previous_mistake_count,
                )
            except Exception:
                logger.exception("Mistake analysis failed for answer_id=%s", answer.id)
                answer.mistake_explanation = "Analysis failed due to an error."
                db.add(answer)
                continue

            answer.error_type = result.error_type
            answer.misconception = result.misconception
            answer.mistake_explanation = result.explanation
            answer.severity = result.severity
            answer.recommended_action = result.recommended_action
            answer.raw_ai_response = result.model_dump(mode="json")
            db.add(answer)

        db.commit()
    finally:
        db.close()
