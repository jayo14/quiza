from types import SimpleNamespace
from unittest.mock import patch


def _upload(client, headers, filename):
    return client.post(
        "/api/v1/materials",
        files={"file": (filename, b"Photosynthesis converts light into energy. " * 4, "text/plain")},
        headers=headers,
    )


def test_upload_only_stores_materials(client, signup):
    headers, _ = signup(email="background-upload@example.com")

    with patch("app.tasks.ingest_material_task.delay") as ingest:
        first = _upload(client, headers, "first.txt")
        second = _upload(client, headers, "second.txt")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["status"] == "uploaded"
    assert second.json()["status"] == "uploaded"
    ingest.assert_not_called()


def test_generation_job_preserves_parameters_and_ownership(client, signup):
    headers, _ = signup(email="background-generation@example.com")
    first = _upload(client, headers, "first.txt").json()
    second = _upload(client, headers, "second.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-task-1"),
    ) as enqueue:
        response = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_ids": [first["id"], second["id"]],
                "number_of_questions": 20,
                "question_types": ["multiple_choice", "true_false"],
            },
            headers=headers,
        )

    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["material_ids"] == [first["id"], second["id"]]
    assert job["question_count"] == 20
    assert job["celery_task_id"] == "celery-task-1"
    enqueue.assert_called_once()
    assert enqueue.call_args.kwargs["question_count"] == 20

    other_headers, _ = signup(email="background-other@example.com")
    assert client.get(f"/api/v1/quizzes/generation-jobs/{job['id']}", headers=other_headers).status_code == 404
