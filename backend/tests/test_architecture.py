"""Architecture isolation tests.

These tests verify that the request-path / background-processing boundary is
correctly maintained:

- Normal API requests (auth, CRUD, listing) must NOT touch Celery or Redis.
- Quiz generation MUST go through Celery (background), not run inline.
- Polling must NOT accidentally trigger another generation task.
- Material upload must NOT trigger RAG processing.
"""

from types import SimpleNamespace
from unittest.mock import patch, MagicMock


def _upload_material(client, headers, filename="test.txt"):
    return client.post(
        "/api/v1/materials",
        files={"file": (filename, b"Some study content about photosynthesis. " * 4, "text/plain")},
        headers=headers,
    )


# --- 1. Sign-in does not call Celery ---


def test_signin_does_not_call_celery(client, signup):
    headers, _ = signup(email="celery-signin@example.com")

    with patch("app.tasks.generate_quiz_task.delay") as mock_celery:
        response = client.post(
            "/api/v1/auth/signin",
            json={"email": "celery-signin@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    mock_celery.assert_not_called()


# --- 2. Sign-in does not call Redis ---


def test_signin_does_not_call_redis(client, signup):
    headers, _ = signup(email="redis-signin@example.com")

    with patch("app.core.celery_app.celery_app.send_task") as mock_redis:
        response = client.post(
            "/api/v1/auth/signin",
            json={"email": "redis-signin@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    mock_redis.assert_not_called()


# --- 3. Material upload does not enqueue processing ---


def test_material_upload_does_not_enqueue_processing(client, signup):
    headers, _ = signup(email="upload-no-celery@example.com")

    with patch("app.tasks.ingest_material_task.delay") as mock_ingest:
        response = _upload_material(client, headers, "study.txt")

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"
    mock_ingest.assert_not_called()


# --- 4. Quiz generation creates a persistent job ---


def test_quiz_generation_creates_persistent_job(client, signup):
    headers, _ = signup(email="job-persist@example.com")
    material = _upload_material(client, headers, "mat.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-job-test"),
    ):
        response = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_id": material["id"],
                "number_of_questions": 5,
                "difficulty": "easy",
                "question_types": ["multiple_choice"],
            },
            headers=headers,
        )

    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "queued"
    assert job["id"] is not None
    assert job["material_ids"] == [material["id"]]
    assert job["question_count"] == 5

    # Verify job persists via GET
    get_resp = client.get(f"/api/v1/quizzes/generation-jobs/{job['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "queued"


# --- 5. Quiz generation enqueues exactly one Celery task ---


def test_quiz_generation_enqueues_exactly_one_celery_task(client, signup):
    headers, _ = signup(email="one-task@example.com")
    material = _upload_material(client, headers, "single.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-one"),
    ) as mock_delay:
        client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_id": material["id"],
                "number_of_questions": 3,
                "question_types": ["true_false"],
            },
            headers=headers,
        )

    assert mock_delay.call_count == 1


# --- 6. HTTP generation request does not wait for task completion ---


def test_http_generation_returns_immediately(client, signup):
    """The /generate-background endpoint must return 202 without blocking
    for the actual quiz generation to complete."""
    import time
    headers, _ = signup(email="immediate-return@example.com")
    material = _upload_material(client, headers, "fast.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-fast"),
    ):
        start = time.perf_counter()
        response = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_id": material["id"],
                "number_of_questions": 10,
                "question_types": ["multiple_choice"],
            },
            headers=headers,
        )
        elapsed = time.perf_counter() - start

    assert response.status_code == 202
    assert elapsed < 2.0, f"Background endpoint took {elapsed:.1f}s — should return immediately"


# --- 7. Polling does not enqueue another task ---


def test_polling_does_not_enqueue_another_task(client, signup):
    headers, _ = signup(email="poll-no-enqueue@example.com")
    material = _upload_material(client, headers, "poll.txt").json()

    # Create a job
    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-poll"),
    ):
        job_resp = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_id": material["id"],
                "number_of_questions": 3,
                "question_types": ["true_false"],
            },
            headers=headers,
        )
    job_id = job_resp.json()["id"]

    # Poll the job — must NOT trigger another Celery task
    with patch("app.tasks.generate_quiz_task.delay") as mock_poll_task:
        poll_resp = client.get(f"/api/v1/quizzes/generation-jobs/{job_id}", headers=headers)
        assert poll_resp.status_code == 200
        mock_poll_task.assert_not_called()


# --- 8. Normal material retrieval does not invoke Celery ---


def test_material_listing_does_not_invoke_celery(client, signup):
    headers, _ = signup(email="list-materials@example.com")
    _upload_material(client, headers, "a.txt")
    _upload_material(client, headers, "b.txt")

    with patch("app.tasks.generate_quiz_task.delay") as mock_celery:
        response = client.get("/api/v1/materials", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_celery.assert_not_called()


# --- 9. Normal quiz retrieval does not invoke Celery ---


def test_quiz_listing_does_not_invoke_celery(client, signup):
    from tests.fakes import generate_quiz_with_fakes, true_false_questions

    headers, _ = signup(email="list-quizzes@example.com")
    material = _upload_material(client, headers, "quiz-list.txt").json()

    generate_quiz_with_fakes(
        client, headers,
        material_id=material["id"],
        questions=true_false_questions("Topic", 2),
    )

    with patch("app.tasks.generate_quiz_task.delay") as mock_celery:
        response = client.get("/api/v1/quizzes", headers=headers)

    assert response.status_code == 200
    mock_celery.assert_not_called()
