import asyncio
from unittest.mock import patch

from tests.fakes import FakeEmbeddingProvider, generate_quiz_with_fakes, true_false_questions


def _setup_ready_quiz(client, headers, *, topic="Photosynthesis", count=4, correct_answer="True"):
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        upload = client.post(
            "/api/v1/materials",
            files={"file": ("notes.txt", b"Photosynthesis converts light into energy. " * 20, "text/plain")},
            headers=headers,
        )
        from app.ai.rag.ingestion import run_ingestion_for_material
        asyncio.run(run_ingestion_for_material(upload.json()["id"]))
    material_id = upload.json()["id"]

    questions = true_false_questions(topic, count, correct_answer=correct_answer)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=questions, question_types=["true_false"]
    )
    body = generated.json()
    return body["id"], [q["id"] for q in body["questions"]]


def test_start_attempt_creates_in_progress_attempt(client, signup):
    headers, _ = signup()
    quiz_id, _ = _setup_ready_quiz(client, headers)

    response = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["total_questions"] == 4


def test_submit_attempt_scores_correctly(client, signup):
    headers, _ = signup()
    quiz_id, question_ids = _setup_ready_quiz(client, headers, count=4, correct_answer="True")

    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()

    answers = [
        {"question_id": question_ids[0], "selected_answer": "True"},
        {"question_id": question_ids[1], "selected_answer": "True"},
        {"question_id": question_ids[2], "selected_answer": "False"},
        {"question_id": question_ids[3], "selected_answer": "False"},
    ]
    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["correct_count"] == 2
    assert body["incorrect_count"] == 2
    assert body["accuracy"] == 0.5
    assert len(body["answers"]) == 4
    assert body["topic_performance"][0]["topic"] == "Photosynthesis"


def test_cannot_submit_the_same_attempt_twice(client, signup):
    headers, _ = signup()
    quiz_id, question_ids = _setup_ready_quiz(client, headers, count=2)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()

    answers = [{"question_id": qid, "selected_answer": "True"} for qid in question_ids]
    first = client.post(f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers)
    assert second.status_code == 422


def test_unanswered_questions_are_marked_incorrect(client, signup):
    headers, _ = signup()
    quiz_id, question_ids = _setup_ready_quiz(client, headers, count=2)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()

    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": []}, headers=headers
    )
    body = response.json()
    assert body["correct_count"] == 0
    assert body["incorrect_count"] == 2


def test_user_cannot_access_another_users_attempt(client, signup):
    headers_a, _ = signup(email="attempta@example.com")
    headers_b, _ = signup(email="attemptb@example.com")

    quiz_id, _ = _setup_ready_quiz(client, headers_a)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers_a).json()

    response = client.get(f"/api/v1/attempts/{attempt['id']}", headers=headers_b)
    assert response.status_code == 404


def test_list_attempts_only_returns_own_attempts(client, signup):
    headers_a, _ = signup(email="lista@example.com")
    headers_b, _ = signup(email="listb@example.com")

    quiz_id, _ = _setup_ready_quiz(client, headers_a)
    client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers_a)

    assert len(client.get("/api/v1/attempts", headers=headers_a).json()) == 1
    assert len(client.get("/api/v1/attempts", headers=headers_b).json()) == 0
