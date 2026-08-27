from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMProvider
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.quiz_generation import QUIZ_GENERATION_SYSTEM_PROMPT, build_quiz_user_prompt
from app.ai.rag.pipeline import get_context_for_query
from app.core.exceptions import AIServiceError, ValidationFailedError
from app.models.enums import Difficulty, QuestionType


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=1)
    question_type: QuestionType
    options: list[str] | None = None
    correct_answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    difficulty: Difficulty
    source_reference: str | None = None

    @field_validator("options")
    @classmethod
    def _dedupe_options(cls, options: list[str] | None) -> list[str] | None:
        if options is None:
            return None
        seen: list[str] = []
        for option in options:
            if option not in seen:
                seen.append(option)
        return seen


class GeneratedQuiz(BaseModel):
    questions: list[GeneratedQuestion]


def validate_generated_questions(
    questions: list[GeneratedQuestion], *, number_of_questions: int, question_types: list[QuestionType]
) -> list[GeneratedQuestion]:
    """Second validation pass beyond Pydantic schema checks: enforces the
    business rules an LLM can still violate even inside valid JSON (wrong option
    count, answer not among options, disallowed question type, near-duplicates)."""

    valid: list[GeneratedQuestion] = []
    seen_texts: set[str] = set()
    allowed_types = set(question_types)

    for q in questions:
        if q.question_type not in allowed_types:
            continue

        normalized = " ".join(q.question.lower().split())
        if normalized in seen_texts:
            continue

        if q.question_type == QuestionType.MULTIPLE_CHOICE:
            if not q.options or len(q.options) < 2 or q.correct_answer not in q.options:
                continue
        elif q.question_type == QuestionType.TRUE_FALSE:
            if q.correct_answer not in ("True", "False"):
                continue
        # short_answer: no structural constraint beyond non-empty, already enforced.

        seen_texts.add(normalized)
        valid.append(q)

    if not valid:
        raise AIServiceError(
            "The AI provider did not return any valid, usable questions for this material."
        )

    return valid[:number_of_questions]


async def generate_quiz_questions(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    number_of_questions: int,
    difficulty: Difficulty,
    question_types: list[QuestionType],
    llm: LLMProvider | None = None,
) -> list[GeneratedQuestion]:
    context = await get_context_for_query(
        db,
        user_id=user_id,
        query=f"key concepts, facts, and definitions suitable for {difficulty.value} quiz questions",
        material_id=material_id,
        top_k=max(number_of_questions, 8),
    )
    if not context.text:
        raise ValidationFailedError(
            "This material has no processed content to generate a quiz from yet."
        )

    provider = llm or get_llm_provider()
    result = await provider.generate_structured(
        system_prompt=QUIZ_GENERATION_SYSTEM_PROMPT,
        user_prompt=build_quiz_user_prompt(
            context=context.text,
            number_of_questions=number_of_questions,
            difficulty=difficulty.value,
            question_types=[t.value for t in question_types],
        ),
        response_model=GeneratedQuiz,
    )

    return validate_generated_questions(
        result.questions, number_of_questions=number_of_questions, question_types=question_types
    )
