from sqlalchemy.orm import Session

from app.ai.llm.base import LLMProvider
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.practice_generation import (
    PRACTICE_GENERATION_SYSTEM_PROMPT,
    build_practice_user_prompt,
)
from app.ai.quiz_generator import GeneratedQuestion, GeneratedQuiz, validate_generated_questions
from app.ai.rag.pipeline import get_context_for_query
from app.core.exceptions import ValidationFailedError
from app.models.enums import QuestionType


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
    result = await provider.generate_structured(
        system_prompt=PRACTICE_GENERATION_SYSTEM_PROMPT,
        user_prompt=build_practice_user_prompt(
            context=context.text,
            number_of_questions=number_of_questions,
            question_types=[t.value for t in question_types],
            weak_topics=weak_topics,
            known_misconceptions=known_misconceptions or "(none recorded yet)",
            previously_asked=previously_asked or "(none yet)",
        ),
        response_model=GeneratedQuiz,
    )

    return validate_generated_questions(
        result.questions, number_of_questions=number_of_questions, question_types=question_types
    )
