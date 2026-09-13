"""Fake AI provider implementations used across the test suite so no test ever
makes a real OpenAI call or consumes real credits."""

import json
from types import SimpleNamespace

from app.ai.llm.base import LLMProvider
from app.ai.rag.pipeline import RetrievedContext


class FakeEmbeddingProvider:
    dimensions = 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float((len(t) * (i + 1)) % 7) for i in range(8)] for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self.embed_one(text)


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
    """Enqueues a quiz via /quizzes/generate-background, executes the Celery task
    directly (bypassing Redis), and returns the completed job response.

    This exercises the full generation pipeline without requiring a running
    Celery worker or Redis instance."""
    from unittest.mock import patch
    from app.tasks import generate_quiz_task
    from tests.fakes import FakeEmbeddingProvider, fake_get_context_for_query, FakeQuizLLM

    payload = {
        "material_id": material_id,
        "number_of_questions": len(questions),
        "difficulty": "medium",
        "question_types": ["multiple_choice", "true_false", "short_answer"],
        **payload_overrides,
    }

    # Step 1: Enqueue via background endpoint (mocks .delay())
    with patch("app.tasks.generate_quiz_task.delay") as mock_delay:
        mock_delay.return_value = SimpleNamespace(id="test-task-id")
        enqueue_resp = client.post("/api/v1/quizzes/generate-background", json=payload, headers=headers)

    assert enqueue_resp.status_code == 202, enqueue_resp.text
    job = enqueue_resp.json()
    job_id = job["id"]

    # Step 2: Execute the task directly (synchronously) with AI fakes
    from app.db.session import SessionLocal
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus

    # Get user_id from the job
    db = SessionLocal()
    db_job = db.get(GenerationJob, job_id)
    user_id = db_job.user_id
    db.close()

    with (
        patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()),
        patch("app.ai.quiz_generator.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.quiz_generator.get_llm_provider", return_value=FakeQuizLLM(questions)),
    ):
        result = generate_quiz_task(
            job_id=job_id,
            user_id=user_id,
            material_ids=[material_id],
            question_count=len(questions),
            difficulty=payload["difficulty"],
            question_types=payload["question_types"],
        )

    assert result["status"] == "completed", f"Task failed: {result}"

    # Step 3: Fetch the completed quiz via the job's quiz_id
    from app.db.session import SessionLocal
    from app.models.generation_job import GenerationJob

    db = SessionLocal()
    db_job = db.get(GenerationJob, job_id)
    quiz_id = db_job.quiz_id
    db.close()

    return client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers)


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
