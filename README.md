# Quiza

An AI-powered study platform that turns your learning materials into quizzes, analyzes your mistakes, discovers your weaknesses, and gives you personalized practice to improve.

Quiza is a full-stack learning platform: upload study materials, generate quizzes grounded in that material via RAG, take them, and get AI-driven mistake analysis, weakness detection, learning summaries, and targeted practice.

Core loop: **Upload Material → Background Processing → RAG Quiz Generation → Interactive Attempt → AI Mistake Analysis → Weakness Detection → Personalized Practice → Track Improvement**

---

## Tech Stack

### Frontend
- **Framework & Build Tool**: React 19, Vite
- **Styling**: Modern CSS / CSS Modules
- **Linting**: Oxlint

### Backend
- **Framework**: FastAPI (Python 3.10+) + Pydantic v2 / Pydantic Settings
- **Database & ORM**: SQLAlchemy 2.0 + Alembic migrations
- **Local Database**: SQLite (default, zero extra infra)
- **Production Database**: PostgreSQL with `pgvector` extension
- **Authentication**: JWT (`python-jose`) + `bcrypt` password hashing
- **Document Processing**: PyMuPDF (PDF), `python-docx` (DOC/DOCX), `pytesseract` (OCR)

### AI & RAG Engine
- **LLM & Embeddings**: OpenAI (`gpt-4o-mini` / `text-embedding-3-small`) behind abstract provider interfaces (`LLMProvider`, `EmbeddingProvider`)
- **Vector Store**: Pluggable `VectorStore` interface with SQLite cosine distance (local) and `pgvector` (production)
- **RAG Retrieval**: Grounded retrieval scoped strictly to user ownership

---

## Project Layout

```text
quiza/
├── frontend/                        # Web application (React + Vite)
│   ├── src/                         # React components, styles, and assets
│   ├── public/                      # Static assets and icons
│   ├── package.json                 # Dependencies and npm scripts
│   ├── vite.config.js               # Vite build configuration
│   └── .oxlintrc.json               # Oxlint configuration
│
└── backend/                         # FastAPI backend & AI engine
    ├── app/
    │   ├── main.py                  # FastAPI entrypoint, CORS, middleware
    │   ├── core/                    # App settings, JWT security, rate limits, exceptions
    │   ├── api/v1/                  # REST API endpoints (auth, materials, quizzes, attempts, analytics)
    │   ├── models/                  # SQLAlchemy ORM models
    │   ├── schemas/                 # Pydantic validation schemas
    │   ├── services/                # Business logic layers
    │   ├── ai/                      # AI & RAG system
    │   │   ├── llm/                 # LLMProvider interface & OpenAI driver
    │   │   ├── embeddings/          # EmbeddingProvider interface & OpenAI driver
    │   │   ├── vectorstore/         # VectorStore abstraction (SQLite & pgvector)
    │   │   ├── rag/                 # File ingestion, chunking, retrieval
    │   │   ├── prompts/             # Prompt engineering templates
    │   │   ├── quiz_generator.py    # RAG quiz generation
    │   │   ├── answer_analyzer.py    # AI mistake analysis
    │   │   ├── weakness_detector.py # Algorithmic weakness aggregation
    │   │   ├── summary_generator.py # Learning summary generation
    │   │   └── practice_generator.py# Targeted practice questions
    │   ├── storage/                 # Document storage providers
    │   └── db/                      # Database connection and session management
    ├── alembic/                     # Database migrations
    ├── tests/                       # Pytest test suite with mocked AI providers
    ├── Dockerfile                   # Backend Docker build script
    └── docker-compose.yml           # Local container orchestration
```

---

## Getting Started

### Prerequisites
- **Node.js** (v18+) & **npm**
- **Python** (3.10+)
- **OpenAI API Key** (for AI features)

---

### 1. Frontend Setup

Navigate to the `frontend/` directory, install dependencies, and start the development server:

```bash
cd frontend
npm install
npm run dev
```

The frontend development server will run at `http://localhost:5173`.

#### Available Frontend Scripts
- `npm run dev` — Starts Vite development server with HMR.
- `npm run build` — Builds production-ready static assets into `dist/`.
- `npm run lint` — Runs Oxlint for code linting.
- `npm run preview` — Previews the production build locally.

---

### 2. Backend Setup

Navigate to the `backend/` directory, create a virtual environment, install dependencies, and set up environment variables:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Environment Variables
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key environment variables:
| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Relational database connection string | `sqlite:///./quiza.db` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | (Required in production) |
| `OPENAI_API_KEY` | OpenAI key for RAG & quiz generation | (Required for AI endpoints) |
| `VECTOR_STORE_BACKEND` | Vector storage backend (`sqlite` or `pgvector`) | `sqlite` |
| `STORAGE_DIR` | Directory for uploaded material files | `./storage_data` |
| `AI_RATE_LIMIT_PER_MINUTE` | Rate limit for AI endpoints per user | `10` |

#### Database Setup & Migrations
Apply database migrations with Alembic:

```bash
alembic upgrade head
```

#### Running the Backend API
Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

- **API Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

#### Running with Docker
Alternatively, run the backend using Docker Compose:

```bash
cd backend
docker compose up --build
```

---

## Running Backend Tests

Run the pytest suite:

```bash
cd backend
pytest
```

All AI calls (`LLMProvider`/`EmbeddingProvider`) are automatically mocked in tests via `tests/fakes.py` so running tests does not consume OpenAI credits or require network access.

---

## AI & RAG System Architecture

1. **Ingestion**: Uploading material via `POST /api/v1/materials` triggers background parsing, chunking, embedding, and vector storage.
2. **Retrieval**: Vector retrieval is strictly scoped to the requesting `user_id` at both vector-store and relational database layers.
3. **Structured AI Generation**: LLM outputs (quizzes, analysis, summaries) are validated against Pydantic models with automatic single-retry error feedback on schema mismatch.

---

## Example API Requests

```bash
# 1. Sign Up
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"password123","name":"Student"}'

# 2. Upload Material (use access_token from signup response)
curl -X POST http://localhost:8000/api/v1/materials \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@lecture_notes.pdf"

# 3. Generate Quiz (when material status is "ready")
curl -X POST http://localhost:8000/api/v1/quizzes/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"material_id":"<id>","number_of_questions":10,"difficulty":"medium","question_types":["multiple_choice","true_false"]}'

# 4. Start & Submit Quiz Attempt
curl -X POST http://localhost:8000/api/v1/quizzes/<quiz_id>/attempts -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/v1/attempts/<attempt_id>/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":"<id>","selected_answer":"True"}]}'

# 5. Fetch Weaknesses, Learning Summary & Generate Targeted Practice
curl http://localhost:8000/api/v1/analytics/weaknesses -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/v1/attempts/<attempt_id>/summary -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/v1/practice/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"material_id":"<id>","number_of_questions":5}'
```

---

## Security Notes

- Passwords hashed with `bcrypt`; JWT authentication with configurable secret keys.
- Data access is isolated per user; resources checked for ownership returning `404 Not Found` for unauthorized access.
- Question answers and explanations are hidden until quiz attempts are submitted.
- Per-user rate limiting on AI generation endpoints to prevent abuse.
