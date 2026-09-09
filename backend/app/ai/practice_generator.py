import logging
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMProvider
from app.ai.llm.context_manager import GenerationContextManager
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.practice_generation import (
    PRACTICE_GENERATION_SYSTEM_PROMPT,
    build_practice_user_prompt,
)
from app.ai.quiz_generator import (
    GeneratedQuestion,
    GeneratedQuiz,
    filter_valid_questions,
    validate_generated_questions,
)
from app.ai.rag.pipeline import get_context_for_query
from app.core.exceptions import AIServiceError, ValidationFailedError
from app.models.enums import QuestionType

logger = logging.getLogger(__name__)


async def generate_practice_questions(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    number_of_questions: int,
    question_types: list[QuestionType],
    weak_topics: list[str],
    known_misconceptions: str,
    previously_asked: str,
    llm: LLMProvider | None = None,
) -> list[GeneratedQuestion]:
    query = "concepts related to: " + ", ".join(weak_topics)
    context = await get_context_for_query(
        db, user_id=user_id, query=query, material_id=material_id, top_k=max(number_of_questions, 8)
    )
    if not context.text:
        raise ValidationFailedError(
            "No processed material content is available to generate practice questions from."
        )

    provider = llm or get_llm_provider()
    ctx_mgr = GenerationContextManager(target_count=number_of_questions)

    max_rounds = 3
    for _ in range(max_rounds):
        if ctx_mgr.is_complete:
            break

        continuation = ctx_mgr.build_continuation_prompt(
            summary_fn=lambda q: f"[{q.question_type.value}] {q.question}"
        )
        base_prompt = build_practice_user_prompt(
            context=context.text,
            number_of_questions=ctx_mgr.remaining_count,
            question_types=[t.value for t in question_types],
            weak_topics=weak_topics,
            known_misconceptions=known_misconceptions or "(none recorded yet)",
            previously_asked=previously_asked or "(none yet)",
        )
        user_prompt = base_prompt + continuation

        try:
            result = await provider.generate_structured(
                system_prompt=PRACTICE_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=GeneratedQuiz,
            )
            valid = filter_valid_questions(result.questions, question_types=question_types)
            ctx_mgr.add_unique(valid, key_fn=lambda q: q.question)
        except Exception as exc:
            if ctx_mgr.accumulated:
                logger.warning(
                    "Error during practice continuation round (%s), returning %d questions already accumulated.",
                    exc,
                    len(ctx_mgr.accumulated),
                )
                break
            raise exc

    if not ctx_mgr.accumulated:
        raise AIServiceError("The AI provider did not return any valid, usable questions for this material.")

    return ctx_mgr.accumulated[:number_of_questions]
