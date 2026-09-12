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


def test_submitting_the_same_attempt_twice_is_idempotent(client, signup):
    headers, _ = signup()
    quiz_id, question_ids = _setup_ready_quiz(client, headers, count=2)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()

    answers = [{"question_id": qid, "selected_answer": "True"} for qid in question_ids]
    first = client.post(f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    second = client.post(f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "completed"
    assert second.json()["id"] == attempt["id"]


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


def test_start_attempt_handles_multiple_in_progress_attempts(client, signup):
    from app.db.session import SessionLocal
    from app.models.attempt import QuizAttempt
    from app.models.enums import AttemptStatus
    from datetime import datetime, timezone, timedelta

    headers, user_data = signup(email="multattempts@example.com")
    quiz_id, _ = _setup_ready_quiz(client, headers)

    # Insert two in-progress attempts manually to simulate concurrency or race condition
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    att1 = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_data["id"],
        status=AttemptStatus.IN_PROGRESS,
        started_at=now - timedelta(minutes=5),
        total_questions=4,
    )
    att2 = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_data["id"],
        status=AttemptStatus.IN_PROGRESS,
        started_at=now,
        total_questions=4,
    )
    db.add_all([att1, att2])
    db.commit()
    att2_id = att2.id
    db.close()

    # Calling start_attempt should not raise MultipleResultsFound
    response = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers)
    assert response.status_code in (200, 201)
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["id"] == att2_id


def test_quiz_can_be_taken_multiple_times_and_attempts_tracked(client, signup):
    headers, _ = signup()
    quiz_id, question_ids = _setup_ready_quiz(client, headers, count=2)

    # Attempt 1: Start and submit
    att1_res = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers)
    assert att1_res.status_code in (200, 201)
    att1 = att1_res.json()

    answers1 = [{"question_id": qid, "selected_answer": "True"} for qid in question_ids]
    sub1_res = client.post(f"/api/v1/attempts/{att1['id']}/submit", json={"answers": answers1}, headers=headers)
    assert sub1_res.status_code == 200
    assert sub1_res.json()["status"] == "completed"

    # Attempt 2: Retake same quiz (should create a new attempt)
    att2_res = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers)
    assert att2_res.status_code in (200, 201)
    att2 = att2_res.json()
    assert att2["id"] != att1["id"]
    assert att2["status"] == "in_progress"

    answers2 = [{"question_id": qid, "selected_answer": "False"} for qid in question_ids]
    sub2_res = client.post(f"/api/v1/attempts/{att2['id']}/submit", json={"answers": answers2}, headers=headers)
    assert sub2_res.status_code == 200
    assert sub2_res.json()["status"] == "completed"

    # Check that both attempts are tracked in user's attempt history
    list_res = client.get("/api/v1/attempts", headers=headers)
    assert list_res.status_code == 200
    attempts_list = list_res.json()
    attempt_ids = [a["id"] for a in attempts_list]
    assert att1["id"] in attempt_ids
    assert att2["id"] in attempt_ids
    assert len(attempts_list) >= 2

