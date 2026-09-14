import pytest
from unittest.mock import AsyncMock, patch

from app.ai.llm.base import LLMProvider
from app.ai.llm.context_manager import GenerationContextManager
from app.ai.llm.failover import FailoverLLMProvider
from app.ai.quiz_generator import GeneratedQuestion, GeneratedQuiz, generate_quiz_questions
from app.core.exceptions import AIServiceError
from app.models.enums import Difficulty, QuestionType
from tests.fakes import fake_get_context_for_query


class MockFailingProvider(LLMProvider):
    def __init__(self, name: str, fail: bool = True, exception: Exception | None = None) -> None:
        self.provider_name = name
        self.fail = fail
        self.exception = exception or AIServiceError("503 UNAVAILABLE: Model experiencing high demand.")
        self.calls = 0

    def is_available(self) -> bool:
        return True

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.fail:
            raise self.exception
        return '{"questions": []}'


class MockSuccessProvider(LLMProvider):
    def __init__(self, name: str, response_json: str) -> None:
        self.provider_name = name
        self.response_json = response_json
        self.calls = 0

    def is_available(self) -> bool:
        return True

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self.response_json


@pytest.mark.asyncio
async def test_failover_when_primary_provider_fails():
    prov1 = MockFailingProvider("gemini", fail=True)
    prov2 = MockSuccessProvider("openai", response_json='{"status": "ok"}')

    router = FailoverLLMProvider(providers=[prov1, prov2])
    result = await router.complete(system_prompt="sys", user_prompt="usr")

    assert result == '{"status": "ok"}'
    assert prov1.calls == 1
    assert prov2.calls == 1


@pytest.mark.asyncio
async def test_failover_structured_generation_reaches_nvidia():
    prov1 = MockFailingProvider("gemini", fail=True)
    prov2 = MockFailingProvider("openai", fail=True)
    prov3 = MockSuccessProvider(
        "nvidia_nim",
        response_json="""{
            "questions": [
                {
                    "question": "What is Python?",
                    "question_type": "multiple_choice",
                    "options": ["A language", "A snake"],
                    "correct_answer": "A language",
                    "explanation": "Programming language",
                    "topic": "Programming",
                    "difficulty": "easy"
                }
            ]
        }""",
    )

    router = FailoverLLMProvider(providers=[prov1, prov2, prov3])
    quiz = await router.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        response_model=GeneratedQuiz,
    )

    assert len(quiz.questions) == 1
    assert quiz.questions[0].question == "What is Python?"
    assert prov1.calls == 1
    assert prov2.calls == 1
    assert prov3.calls == 1


def test_generation_context_manager_tracks_uniqueness_and_continuation():
    ctx = GenerationContextManager(target_count=3)
    assert ctx.remaining_count == 3
    assert not ctx.is_complete

    q1 = GeneratedQuestion(
        question="What is DNA?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        options=["Genetic material", "Protein"],
        correct_answer="Genetic material",
        explanation="Deoxyribonucleic acid",
        topic="Biology",
        difficulty=Difficulty.EASY,
    )
    # Adding q1
    added = ctx.add_unique([q1], key_fn=lambda q: q.question)
    assert len(added) == 1
    assert ctx.remaining_count == 2
    assert not ctx.is_complete

    # Duplicate should not be added
    q1_dup = GeneratedQuestion(
        question="what is dna?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        options=["Genetic material", "Protein"],
        correct_answer="Genetic material",
        explanation="Deoxyribonucleic acid",
        topic="Biology",
        difficulty=Difficulty.EASY,
    )
    added_dup = ctx.add_unique([q1_dup], key_fn=lambda q: q.question)
    assert len(added_dup) == 0
    assert len(ctx.accumulated) == 1

    # Continuation prompt mentions q1
    prompt = ctx.build_continuation_prompt(summary_fn=lambda q: q.question)
    assert "What is DNA?" in prompt
    assert "2 unique item(s)" in prompt


@pytest.mark.asyncio
async def test_midtask_continuation_resumes_without_redundancy():
    from app.db.session import SessionLocal

    # Mock LLM that returns 2 questions on call 1, and 1 remaining question on call 2
    class StatefulLLM(LLMProvider):
        def __init__(self):
            self.call_count = 0
            self.received_prompts = []

        async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            self.call_count += 1
            self.received_prompts.append(user_prompt)

            if self.call_count == 1:
                # Return only 2 questions when 3 were requested
                return """{
                    "questions": [
                        {
                            "question": "Q1: First concept?",
                            "question_type": "multiple_choice",
                            "options": ["A", "B"],
                            "correct_answer": "A",
                            "explanation": "Exp 1",
                            "topic": "General",
                            "difficulty": "medium"
                        },
                        {
                            "question": "Q2: Second concept?",
                            "question_type": "multiple_choice",
                            "options": ["C", "D"],
                            "correct_answer": "C",
                            "explanation": "Exp 2",
                            "topic": "General",
                            "difficulty": "medium"
                        }
                    ]
                }"""
            else:
                # Call 2 returns the 3rd question
                return """{
                    "questions": [
                        {
                            "question": "Q3: Third concept?",
                            "question_type": "multiple_choice",
                            "options": ["E", "F"],
                            "correct_answer": "E",
                            "explanation": "Exp 3",
                            "topic": "General",
                            "difficulty": "medium"
                        }
                    ]
                }"""

    mock_llm = StatefulLLM()
    db = SessionLocal()
    try:
        with patch("app.ai.quiz_generator.get_context_for_query", side_effect=fake_get_context_for_query):
            questions = await generate_quiz_questions(
                db,
                user_id="user-123",
                material_id="mat-123",
                number_of_questions=3,
                difficulty=Difficulty.MEDIUM,
                question_types=[QuestionType.MULTIPLE_CHOICE],
                llm=mock_llm,
            )
    finally:
        db.close()

    assert len(questions) == 3
    assert questions[0].question == "Q1: First concept?"
    assert questions[1].question == "Q2: Second concept?"
    assert questions[2].question == "Q3: Third concept?"

    # Verify that call 2 prompt contained continuation context with Q1 and Q2
    assert mock_llm.call_count == 2
    assert "Q1: First concept?" in mock_llm.received_prompts[1]
    assert "Q2: Second concept?" in mock_llm.received_prompts[1]
    assert "Do NOT duplicate" in mock_llm.received_prompts[1]


def test_error_classification_for_404_and_410():
    from app.ai.llm.errors import ErrorCategory, classify_error, should_failover

    class DummyStatusError(Exception):
        def __init__(self, status_code: int, message: str) -> None:
            super().__init__(message)
            self.status_code = status_code

    # 404 model not found
    err_404 = DummyStatusError(404, "Error code: 404 - Not Found")
    assert classify_error(err_404) == ErrorCategory.MODEL_NOT_FOUND
    assert should_failover(err_404) is True

    # 410 model gone / end of life
    err_410 = DummyStatusError(
        410,
        "The model 'meta/llama-3.3-70b-instruct' has reached its end of life on 2026-08-26T09:00:00Z and is no longer available.",
    )
    assert classify_error(err_410) == ErrorCategory.MODEL_NOT_FOUND
    assert should_failover(err_410) is True

    # Message-based detection
    err_text = Exception("Model is no longer available on this platform")
    assert classify_error(err_text) == ErrorCategory.MODEL_NOT_FOUND
    assert should_failover(err_text) is True


@pytest.mark.asyncio
async def test_failover_when_model_is_deprecated_or_not_found():
    from app.ai.llm.errors import ErrorCategory

    class ModelGoneError(Exception):
        status_code = 410

    prov1 = MockFailingProvider("nvidia_nim", fail=True, exception=ModelGoneError("Model reached end of life"))
    prov2 = MockSuccessProvider("gemini", response_json='{"status": "recovered"}')

    router = FailoverLLMProvider(providers=[prov1, prov2])
    result = await router.complete(system_prompt="sys", user_prompt="usr")

    assert result == '{"status": "recovered"}'
    assert prov1.calls == 1
    assert prov2.calls == 1


def test_groq_provider_registered_in_failover():
    from app.ai.llm.groq_provider import GroqProvider

    router = FailoverLLMProvider(providers=[])
    providers_built = router._build_default_providers()
    provider_names = [getattr(p, "provider_name", "") for p in providers_built]
    # Check that GroqProvider is available in the module and implements LLMProvider
    groq = GroqProvider(api_key="gsk-dummy-key")
    assert groq.provider_name == "groq"
    assert groq.is_available() is True

