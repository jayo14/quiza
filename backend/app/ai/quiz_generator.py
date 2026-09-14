import logging
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMProvider
from app.ai.llm.context_manager import GenerationContextManager
from app.ai.llm.openai import get_llm_provider
from app.ai.prompts.quiz_generation import QUIZ_GENERATION_SYSTEM_PROMPT, build_quiz_user_prompt
from app.ai.rag.pipeline import get_context_for_query
from app.core.exceptions import AIServiceError, ValidationFailedError
from app.models.enums import Difficulty, QuestionType

logger = logging.getLogger(__name__)


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


def filter_valid_questions(
    questions: list[GeneratedQuestion], question_types: list[QuestionType]
) -> list[GeneratedQuestion]:
    """Filters questions according to structural business rules."""
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

        seen_texts.add(normalized)
        valid.append(q)

    return valid


def validate_generated_questions(
    questions: list[GeneratedQuestion], *, number_of_questions: int, question_types: list[QuestionType]
) -> list[GeneratedQuestion]:
    """Validates that the model returned exactly the requested number of questions."""
    valid = filter_valid_questions(questions, question_types)
    if len(valid) != number_of_questions:
        raise AIServiceError(
            f"The AI provider returned {len(valid)} valid questions, "
            f"but {number_of_questions} were requested."
        )

    return valid


async def generate_quiz_questions(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    number_of_questions: int,
    difficulty: Difficulty,
    question_types: list[QuestionType],
    llm: LLMProvider | None = None,
    material_ids: list[str] | None = None,
) -> list[GeneratedQuestion]:
    context = await get_context_for_query(
        db,
        user_id=user_id,
        query=f"key concepts, facts, and definitions suitable for {difficulty.value} quiz questions",
        material_id=material_id,
        material_ids=material_ids,
        top_k=max(number_of_questions, 8),
    )
    if not context.text:
        raise ValidationFailedError(
            "This material has no processed content to generate a quiz from yet."
        )

    provider = llm or get_llm_provider()
    ctx_mgr = GenerationContextManager(target_count=number_of_questions)

    # Scale rounds with target count: 1 round for ≤10 questions, 2 for ≤20, 3 for more
    max_rounds = 1 if number_of_questions <= 10 else (2 if number_of_questions <= 20 else 3)
    for _ in range(max_rounds):
        if ctx_mgr.is_complete:
            break

        continuation = ctx_mgr.build_continuation_prompt(
            summary_fn=lambda q: f"[{q.question_type.value}] {q.question}"
        )
        base_prompt = build_quiz_user_prompt(
            context=context.text,
            number_of_questions=ctx_mgr.remaining_count,
            difficulty=difficulty.value,
            question_types=[t.value for t in question_types],
        )
        user_prompt = base_prompt + continuation

        try:
            result = await provider.generate_structured(
                system_prompt=QUIZ_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=GeneratedQuiz,
            )
            valid = filter_valid_questions(result.questions, question_types=question_types)
            ctx_mgr.add_unique(valid, key_fn=lambda q: q.question)
        except Exception as exc:
            if ctx_mgr.accumulated:
                logger.warning(
                    "Error during continuation round (%s), returning %d questions already accumulated.",
                    exc,
                    len(ctx_mgr.accumulated),
                )
                break
            raise exc

    if len(ctx_mgr.accumulated) != number_of_questions:
        raise AIServiceError(
            f"The AI provider returned {len(ctx_mgr.accumulated)} valid questions, "
            f"but {number_of_questions} were requested."
        )

    return ctx_mgr.accumulated
