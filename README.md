# Quiza

An AI-powered study platform that turns your learning materials into quizzes, analyzes your mistakes, discovers your weaknesses, and gives you personalized practice to improve.

AI-powered learning platform backend: upload study materials, generate quizzes
grounded in that material via RAG, take them, and get AI-driven mistake
analysis, weakness detection, learning summaries, and targeted practice.

Backend only — Python/FastAPI. No frontend, no Node.js.

Core loop: **Upload → Process → Generate Quiz → Attempt → Analyze → Detect
Weakness → Explain → Targeted Practice → Track Improvement**

## Stack

- FastAPI + Pydantic / Pydantic Settings
- SQLAlchemy 2.0 + Alembic
- SQLite for local development (swap `DATABASE_URL` for Postgres in production)
- JWT auth (`python-jose`) + `bcrypt` password hashing
- OpenAI for LLM + embeddings, behind provider interfaces (`LLMProvider`,
  `EmbeddingProvider`) so the backend can swap providers without touching callers
- A `VectorStore` abstraction with two implementations: brute-force cosine
  search over a SQLite table (default, zero extra infra) and a pgvector-backed
  implementation for Postgres in production
- PyMuPDF (PDF), `python-docx` (DOC/DOCX), `pytesseract` (OCR for images)

API docs are served by FastAPI's own OpenAPI integration — no extra
documentation framework is needed (`drf-spectacular` is Django REST
Framework-specific and doesn't apply here).

## Project layout

```text
app/
├── main.py              # FastAPI app, middleware, exception handlers
├── core/                 # settings, JWT/password security, rate limiting, exceptions
├── api/v1/                # route handlers only — no business logic here
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic request/response models
├── services/               # business logic, called from routes
├── ai/
│   ├── llm/                  # LLMProvider abstraction + OpenAI implementation
│   ├── embeddings/            # EmbeddingProvider abstraction + OpenAI implementation
│   ├── vectorstore/            # VectorStore abstraction: SQLite + pgvector
│   ├── rag/                     # parsing, chunking, ingestion, retrieval, context assembly
│   ├── prompts/                  # prompt templates, kept out of route handlers
│   ├── quiz_generator.py          # RAG-grounded quiz generation
│   ├── answer_analyzer.py          # structured mistake analysis
│   ├── weakness_detector.py         # deterministic weakness aggregation
│   ├── summary_generator.py          # AI learning summaries
│   └── practice_generator.py          # targeted practice generation
├── storage/                # file storage abstraction (local disk by default)
└── db/                      # engine/session, declarative base

alembic/                     # migrations
tests/                        # pytest suite, all AI calls mocked
```

## Installation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Copy the example file and fill in what you need:

```bash
cp .env.example .env
```

Everything works out of the box for local development except `OPENAI_API_KEY`,
which is required for any endpoint that actually calls the LLM or embeddings
(material processing, quiz generation, mistake analysis, summaries, practice
generation). See `.env.example` for the full list with comments; the
important ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./quiza.db` locally; a Postgres URL in production |
| `JWT_SECRET_KEY` | Must be overridden in production — the app refuses to start with the default if `APP_ENV=production` |
| `OPENAI_API_KEY` | Required for any AI-backed endpoint |
| `VECTOR_STORE_BACKEND` | `sqlite` (default) or `pgvector` |
| `STORAGE_DIR` | Where uploaded files are written locally |
| `AI_RATE_LIMIT_PER_MINUTE` | Per-user limit on quiz/practice generation and summary requests |

## Database setup & migrations

SQLite needs no setup — the file is created on first migration.

```bash
alembic upgrade head          # apply all migrations
alembic revision --autogenerate -m "describe your change"   # after changing models
```

To move to Postgres + pgvector in production: set `DATABASE_URL` to your
Postgres connection string, enable the `pgvector` extension on that database,
set `VECTOR_STORE_BACKEND=pgvector`, install the `pgvector` Python package,
and run `alembic upgrade head` again.

## Running the API

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

Or with Docker:

```bash
cd backend
docker compose up --build
```

## Running tests

```bash
pytest
```

Every test mocks the `LLMProvider`/`EmbeddingProvider` call sites directly
(see `tests/fakes.py`) — no test ever calls OpenAI or spends real credits.
Each test run gets a fresh SQLite database (a temp file created in
`tests/conftest.py`), so tests don't interfere with your local `quiza.db`.

## AI configuration

All AI calls go through `LLMProvider`/`EmbeddingProvider` (`app/ai/llm`,
`app/ai/embeddings`), currently backed by OpenAI (`openai_chat_model` /
`openai_embedding_model` in settings). LLM calls that must return structured
data go through `LLMProvider.generate_structured`, which asks for JSON
matching a Pydantic schema, validates it, and retries once with the
validation error fed back to the model before raising `AIServiceError` — so a
flaky or malformed response never crashes a request, it surfaces as a clean
502.

Prompts live in `app/ai/prompts/`, not inline in route handlers or services.

## RAG configuration

Upload flow: `POST /api/v1/materials` validates and stores the file, creates
a `Material` row (`status=uploaded`), and returns immediately — parsing,
chunking, embedding, and vector storage all run in a background task so
upload latency doesn't scale with document size. Poll
`GET /api/v1/materials/{id}` for `status` (`processing` → `ready`/`failed`).

Retrieval is always scoped to the requesting `user_id` at the vector-store
level (`VectorStore.search` requires it), with a second ownership check at
the relational layer in `app/ai/rag/retrieval.py` — one student's material is
never retrievable by another, even if a future vector store implementation
forgets to filter.

## Example API requests

```bash
# Sign up
curl -X POST localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"a@example.com","password":"password123","name":"A"}'

# Upload a material (use the access_token from signup)
curl -X POST localhost:8000/api/v1/materials \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@notes.pdf"

# Generate a quiz once the material's status is "ready"
curl -X POST localhost:8000/api/v1/quizzes/generate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"material_id":"<id>","number_of_questions":10,"difficulty":"medium","question_types":["multiple_choice","true_false"]}'

# Start and submit an attempt
curl -X POST localhost:8000/api/v1/quizzes/<quiz_id>/attempts -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/api/v1/attempts/<attempt_id>/submit \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":"<id>","selected_answer":"True"}]}'

# Weaknesses, summary, and targeted practice
curl localhost:8000/api/v1/analytics/weaknesses -H "Authorization: Bearer $TOKEN"
curl localhost:8000/api/v1/attempts/<attempt_id>/summary -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/api/v1/practice/generate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"material_id":"<id>","number_of_questions":5}'
```

## Security notes

- Passwords hashed with bcrypt; JWTs signed with `JWT_SECRET_KEY`
- Every resource lookup (`materials`, `quizzes`, `attempts`, `weaknesses`) is
  scoped to the authenticated user — ownership is derived from the JWT, never
  from a client-supplied `user_id`; cross-user access returns `404`, not `403`,
  so ownership can't be probed
- Quiz question endpoints never return `correct_answer`/`explanation` until
  after an attempt is submitted
- Uploads are validated by extension, content type, and size before being
  stored
- AI-heavy endpoints (`quizzes/generate`, `practice/generate`,
  `attempts/{id}/summary`) sit behind a per-user rate limiter
  (`AI_RATE_LIMIT_PER_MINUTE`)
>>>>>>> 934fa9f (Add README, Dockerfile, and docker-compose for local setup)
