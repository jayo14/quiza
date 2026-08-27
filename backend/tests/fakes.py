"""Fake AI provider implementations used across the test suite so no test ever
makes a real OpenAI call or consumes real credits."""

import json

from app.ai.llm.base import LLMProvider
from app.ai.rag.pipeline import RetrievedContext


class FakeEmbeddingProvider:
    dimensions = 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float((len(t) * (i + 1)) % 7) for i in range(8)] for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


class FakeQuizLLM(LLMProvider):
    """Returns a fixed set of questions regardless of prompt, still routed through
    the real LLMProvider.generate_structured so JSON parsing/validation is exercised."""

    def __init__(self, questions: list[dict]) -> None:
        self._questions = questions

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        return json.dumps({"questions": self._questions})


def fake_context(text: str = "[Source: chunk 0]\nPhotosynthesis converts light into energy.") -> RetrievedContext:
    return RetrievedContext(text=text, chunk_ids=["fake-chunk"], source_references=["chunk 0"])


async def fake_get_context_for_query(*args, **kwargs) -> RetrievedContext:
    return fake_context()


def generate_quiz_with_fakes(client, headers, *, material_id: str, questions: list[dict], **payload_overrides):
    """Calls POST /quizzes/generate with the LLM and RAG context mocked out, so no
    real AI call happens. Returns the raw httpx response."""

    from unittest.mock import patch

    payload = {
        "material_id": material_id,
        "number_of_questions": len(questions),
        "difficulty": "medium",
        "question_types": ["multiple_choice", "true_false", "short_answer"],
        **payload_overrides,
    }
    with (
        patch("app.ai.quiz_generator.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.quiz_generator.get_llm_provider", return_value=FakeQuizLLM(questions)),
    ):
        return client.post("/api/v1/quizzes/generate", json=payload, headers=headers)


def true_false_questions(topic: str, count: int, correct_answer: str = "True") -> list[dict]:
    return [
        {
            "question": f"{topic} statement {i}",
            "question_type": "true_false",
            "options": None,
            "correct_answer": correct_answer,
            "explanation": f"Explanation for {topic} {i}.",
            "topic": topic,
            "difficulty": "medium",
            "source_reference": "chunk 0",
        }
        for i in range(count)
    ]
