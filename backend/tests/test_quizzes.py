import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from tests.fakes import FakeEmbeddingProvider, generate_quiz_with_fakes, true_false_questions


def _upload_ready_material(client, headers):
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        response = client.post(
            "/api/v1/materials",
            files={"file": ("notes.txt", b"Photosynthesis converts light into energy. " * 20, "text/plain")},
            headers=headers,
        )
        from app.ai.rag.ingestion import run_ingestion_for_material
        asyncio.run(run_ingestion_for_material(response.json()["id"]))
    return response.json()["id"]


def test_generate_quiz_creates_questions_from_material(client, signup):
    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    questions = true_false_questions("Photosynthesis", 3)

    response = generate_quiz_with_fakes(client, headers, material_id=material_id, questions=questions)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    quiz_id = body["id"]
    questions_resp = client.get(f"/api/v1/quizzes/{quiz_id}/questions", headers=headers)
    assert questions_resp.status_code == 200
    assert len(questions_resp.json()) == 3


def test_quiz_questions_never_expose_correct_answer(client, signup):
    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    questions = true_false_questions("Gravity", 2)

    generated = generate_quiz_with_fakes(client, headers, material_id=material_id, questions=questions)
    quiz_id = generated.json()["id"]

    response = client.get(f"/api/v1/quizzes/{quiz_id}/questions", headers=headers)
    assert response.status_code == 200
    dumped = json.dumps(response.json())
    assert "correct_answer" not in dumped
    assert "explanation" not in dumped


def test_generate_quiz_background_queues_regardless_of_material_status(client, signup):
    """Background endpoint accepts the job; worker validates material readiness at execution time."""
    headers, _ = signup()
    with patch("app.ai.rag.ingestion.get_embedding_provider", side_effect=RuntimeError("boom")):
        upload = client.post(
            "/api/v1/materials",
            files={"file": ("notes.txt", b"some content", "text/plain")},
            headers=headers,
        )
    material_id = upload.json()["id"]

    with patch("app.tasks.generate_quiz_task.delay", return_value=SimpleNamespace(id="task-1")):
        response = client.post(
            "/api/v1/quizzes/generate-background",
            json={"material_ids": [material_id], "number_of_questions": 2},
            headers=headers,
        )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_user_cannot_access_another_users_quiz(client, signup):
    headers_a, _ = signup(email="quiza@example.com")
    headers_b, _ = signup(email="quizb@example.com")

    material_id = _upload_ready_material(client, headers_a)
    generated = generate_quiz_with_fakes(
        client, headers_a, material_id=material_id, questions=true_false_questions("Topic", 2)
    )
    quiz_id = generated.json()["id"]

    assert client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/quizzes/{quiz_id}/questions", headers=headers_b).status_code == 404


def test_list_and_delete_quiz(client, signup):
    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=true_false_questions("Topic", 2)
    )
    quiz_id = generated.json()["id"]

    assert len(client.get("/api/v1/quizzes", headers=headers).json()) == 1

    delete = client.delete(f"/api/v1/quizzes/{quiz_id}", headers=headers)
    assert delete.status_code == 204
    assert client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers).status_code == 404


def test_list_quizzes_excludes_failed_quizzes(client, signup):
    from app.db.session import SessionLocal
    from app.models.quiz import Quiz
    from app.models.enums import QuizStatus

    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=true_false_questions("Topic", 2)
    )
    quiz_id = generated.json()["id"]

    # Mark the quiz as FAILED directly in DB
    db = SessionLocal()
    quiz = db.get(Quiz, quiz_id)
    quiz.status = QuizStatus.FAILED
    db.commit()
    db.close()

    # When listing quizzes, failed quizzes should not be returned
    response = client.get("/api/v1/quizzes", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_list_quizzes_reports_actual_question_count(client, signup):
    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=true_false_questions("Topic", 3)
    )
    assert generated.status_code == 200
    quiz_id = generated.json()["id"]

    response = client.get("/api/v1/quizzes", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == quiz_id
    assert items[0]["question_count"] == 3


def test_true_false_questions_have_default_options(client, signup):
    headers, _ = signup()
    material_id = _upload_ready_material(client, headers)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=true_false_questions("Topic", 2)
    )
    quiz_id = generated.json()["id"]

    response = client.get(f"/api/v1/quizzes/{quiz_id}/questions", headers=headers)
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) == 2
    for q in questions:
        assert q["question_type"] == "true_false"
        assert q["options"] == ["True", "False"]


