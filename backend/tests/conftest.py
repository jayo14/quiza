import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET_KEY"] = "test-only-secret"
os.environ["OPENAI_API_KEY"] = "sk-test-not-real"
os.environ["GEMINI_API_KEY"] = "fake-gemini-key-for-testing"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="quiza-test-storage-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.ai.vectorstore.models  # noqa: E402,F401  registers ChunkEmbedding on Base.metadata
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture
def signup(client: TestClient):
    """Returns a helper that signs up a user and gives back (auth_headers, user_json)."""

    def _signup(email: str = "student@example.com", password: str = "password123", name: str = "Student"):
        response = client.post("/api/v1/auth/signup", json={"email": email, "password": password, "name": name})
        assert response.status_code == 201, response.text
        body = response.json()
        headers = {"Authorization": f"Bearer {body['tokens']['access_token']}"}
        return headers, body["user"]

    return _signup
