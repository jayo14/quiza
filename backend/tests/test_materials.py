from unittest.mock import patch

from tests.fakes import FakeEmbeddingProvider


def _upload_text_material(client, headers, filename="notes.txt", content=None):
    content = content or (b"Photosynthesis converts light into chemical energy. " * 20)
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        return client.post(
            "/api/v1/materials",
            files={"file": (filename, content, "text/plain")},
            headers=headers,
        )


def test_upload_material_stays_uploaded_until_generation(client, signup):
    headers, _ = signup()
    response = _upload_text_material(client, headers)
    assert response.status_code == 201
    material = response.json()
    assert material["status"] == "uploaded"

    detail = client.get(f"/api/v1/materials/{material['id']}", headers=headers)
    assert detail.json()["status"] == "uploaded"


def test_upload_rejects_unsupported_file_type(client, signup):
    headers, _ = signup()
    response = client.post(
        "/api/v1/materials",
        files={"file": ("virus.exe", b"not really a document", "application/octet-stream")},
        headers=headers,
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(client, signup):
    headers, _ = signup()
    from app.core.config import settings

    too_big = b"x" * (settings.max_upload_size_mb * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/materials",
        files={"file": ("big.txt", too_big, "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422


def test_material_upload_requires_authentication(client):
    response = client.post(
        "/api/v1/materials", files={"file": ("notes.txt", b"hello world", "text/plain")}
    )
    assert response.status_code == 401


def test_user_cannot_access_another_users_material(client, signup):
    headers_a, _ = signup(email="owner@example.com")
    headers_b, _ = signup(email="intruder@example.com")

    upload = _upload_text_material(client, headers_a)
    material_id = upload.json()["id"]

    response = client.get(f"/api/v1/materials/{material_id}", headers=headers_b)
    assert response.status_code == 404


def test_list_materials_only_returns_own_materials(client, signup):
    headers_a, _ = signup(email="owner2@example.com")
    headers_b, _ = signup(email="other2@example.com")

    _upload_text_material(client, headers_a)

    assert len(client.get("/api/v1/materials", headers=headers_a).json()) == 1
    assert len(client.get("/api/v1/materials", headers=headers_b).json()) == 0


def test_delete_material_removes_it(client, signup):
    headers, _ = signup()
    upload = _upload_text_material(client, headers)
    material_id = upload.json()["id"]

    delete = client.delete(f"/api/v1/materials/{material_id}", headers=headers)
    assert delete.status_code == 204

    get_after_delete = client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert get_after_delete.status_code == 404


def test_delete_material_with_associated_quizzes_succeeds(client, signup):
    from unittest.mock import patch
    import asyncio
    from tests.fakes import FakeEmbeddingProvider, generate_quiz_with_fakes, true_false_questions

    headers, _ = signup()
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        upload = _upload_text_material(client, headers)
        material_id = upload.json()["id"]
        from app.ai.rag.ingestion import run_ingestion_for_material
        asyncio.run(run_ingestion_for_material(material_id))

    # Generate a quiz associated with this material
    quiz_res = generate_quiz_with_fakes(client, headers, material_id=material_id, questions=true_false_questions("Topic", 2))
    assert quiz_res.status_code == 201

    # Deleting material should delete cleanly without NotNullViolation on quizzes.material_id
    delete = client.delete(f"/api/v1/materials/{material_id}", headers=headers)
    assert delete.status_code == 204

    # Ensure material is gone
    get_mat = client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert get_mat.status_code == 404

