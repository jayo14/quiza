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


def test_multiple_materials_remain_available_without_processing(client, signup):
    headers, _ = signup(email="multi-mat@example.com")

    with patch("app.tasks.ingest_material_task.delay") as ingest:
        m1 = _upload(client, headers, "doc1.txt").json()
        m2 = _upload(client, headers, "doc2.txt").json()
        m3 = _upload(client, headers, "doc3.txt").json()

    assert m1["status"] == "uploaded"
    assert m2["status"] == "uploaded"
    assert m3["status"] == "uploaded"
    ingest.assert_not_called()

    list_resp = client.get("/api/v1/materials", headers=headers)
    assert list_resp.status_code == 200
    materials = list_resp.json()
    assert len(materials) == 3
    assert {m["id"] for m in materials} == {m1["id"], m2["id"], m3["id"]}


def test_generate_quiz_task_execution_end_to_end(client, signup):
    headers, user_body = signup(email="task-e2e@example.com")
    user_id = user_body["id"]

    first = _upload(client, headers, "mat1.txt").json()
    second = _upload(client, headers, "mat2.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-task-e2e"),
    ):
        post_job = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_ids": [first["id"], second["id"]],
                "question_count": 10,
                "difficulty": "medium",
                "question_types": ["true_false"],
            },
            headers=headers,
        )

    assert post_job.status_code == 202
    job_id = post_job.json()["id"]

    from tests.fakes import FakeEmbeddingProvider, FakeQuizLLM, fake_get_context_for_query, true_false_questions
    from app.tasks import generate_quiz_task

    questions = true_false_questions("Photosynthesis", 10)
    with (
        patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()),
        patch("app.ai.quiz_generator.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.quiz_generator.get_llm_provider", return_value=FakeQuizLLM(questions)),
    ):
        res = generate_quiz_task(
            job_id=job_id,
            user_id=user_id,
            material_ids=[first["id"], second["id"]],
            question_count=10,
            difficulty="medium",
            question_types=["true_false"],
        )

    assert res["status"] == "completed"
    quiz_id = res["quiz_id"]
    assert quiz_id is not None

    job_detail = client.get(f"/api/v1/quizzes/generation-jobs/{job_id}", headers=headers).json()
    assert job_detail["status"] == "completed"
    assert job_detail["progress"] == 100
    assert job_detail["current_stage"] == "completed"
    assert job_detail["quiz_id"] == quiz_id

    quiz_resp = client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers)
    assert quiz_resp.status_code == 200
    assert quiz_resp.json()["number_of_questions"] == 10

    questions_resp = client.get(f"/api/v1/quizzes/{quiz_id}/questions", headers=headers)
    assert questions_resp.status_code == 200
    question_items = questions_resp.json()
    assert len(question_items) == 10

    # Idempotency check: invoking the task a second time should return already_completed
    repeat_res = generate_quiz_task(
        job_id=job_id,
        user_id=user_id,
        material_ids=[first["id"], second["id"]],
        question_count=10,
        difficulty="medium",
        question_types=["true_false"],
    )
    assert repeat_res["status"] == "already_completed"
    assert repeat_res["quiz_id"] == quiz_id


def test_retry_generation_job(client, signup):
    headers, user_body = signup(email="retry-job@example.com")
    mat = _upload(client, headers, "retry_mat.txt").json()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-task-retry"),
    ):
        post_job = client.post(
            "/api/v1/quizzes/generate-background",
            json={
                "material_ids": [mat["id"]],
                "question_count": 5,
                "difficulty": "easy",
                "question_types": ["multiple_choice"],
            },
            headers=headers,
        )
    assert post_job.status_code == 202
    job_id = post_job.json()["id"]

    # Mark the job as failed
    from app.db.session import SessionLocal
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus

    db = SessionLocal()
    db_job = db.get(GenerationJob, job_id)
    db_job.status = GenerationJobStatus.FAILED
    db_job.error_message = "Generation timed out. Please try again."
    db.commit()
    db.close()

    with patch(
        "app.tasks.generate_quiz_task.delay",
        return_value=SimpleNamespace(id="celery-task-retried"),
    ) as mock_delay:
        retry_resp = client.post(
            f"/api/v1/quizzes/generation-jobs/{job_id}/retry",
            headers=headers,
        )
        assert retry_resp.status_code == 202
        retried = retry_resp.json()
        assert retried["id"] == job_id
        assert retried["status"] == "queued"
        assert retried["progress"] == 0
        mock_delay.assert_called_once()
