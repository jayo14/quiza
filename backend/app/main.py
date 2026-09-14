import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import QuizaError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Quiza API",
    description=(
        "Backend API for Quiza: upload learning materials, generate quizzes with RAG, "
        "attempt them, and get AI-driven mistake analysis, weakness detection, and "
        "targeted practice."
    ),
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status code, and duration in milliseconds.

    Skips health-check endpoints to avoid noise. Only logs slow requests
    (>500ms) at WARNING level; everything else at DEBUG.
    """

    _SKIP_PATHS = {"/health", "/ping", f"{settings.api_v1_prefix}/health", f"{settings.api_v1_prefix}/ping"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        log_fn = logger.warning if duration_ms > 500 else logger.debug
        log_fn(
            "request=%s %s status=%d duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


app.add_middleware(RequestTimingMiddleware)


def _get_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    headers: dict[str, str] = {}
    if origin and (origin in settings.cors_origin_list or "*" in settings.cors_origin_list):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"
    elif origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


@app.exception_handler(QuizaError)
def handle_quiza_error(request: Request, exc: QuizaError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_get_cors_headers(request),
    )


@app.exception_handler(SQLAlchemyError)
def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error occurred while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is temporarily unreachable. Please try again shortly."},
        headers=_get_cors_headers(request),
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "The server could not complete the request. Please try again."},
        headers=_get_cors_headers(request),
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def recover_stale_states():
    from app.db.session import SessionLocal
    from app.models.material import Material
    from app.models.quiz import Quiz
    from app.models.generation_job import GenerationJob
    from app.models.enums import GenerationJobStatus, MaterialStatus, QuizStatus

    db = SessionLocal()
    try:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

        stale_materials = db.query(Material).filter(
            Material.status == MaterialStatus.PROCESSING,
            Material.updated_at < threshold,
        ).all()
        for mat in stale_materials:
            mat.status = MaterialStatus.FAILED
            mat.processing_error = "Processing timed out. Please try again."
            db.add(mat)
        if stale_materials:
            logger.warning("Recovered %d stale materials stuck in PROCESSING", len(stale_materials))

        stale_quizzes = db.query(Quiz).filter(
            Quiz.status == QuizStatus.GENERATING,
            Quiz.updated_at < threshold,
        ).all()
        for quiz in stale_quizzes:
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = "Generation timed out. Please try again."
            db.add(quiz)
        if stale_quizzes:
            logger.warning("Recovered %d stale quizzes stuck in GENERATING", len(stale_quizzes))

        stale_jobs = db.query(GenerationJob).filter(
            GenerationJob.status == GenerationJobStatus.PROCESSING,
            GenerationJob.updated_at < threshold,
        ).all()
        for job in stale_jobs:
            job.status = GenerationJobStatus.FAILED
            job.current_stage = "failed"
            job.error_message = "Generation timed out. Please try again."
            job.completed_at = datetime.now(timezone.utc)
            db.add(job)
        if stale_jobs:
            logger.warning("Recovered %d stale generation jobs", len(stale_jobs))

        db.commit()
    except Exception:
        logger.exception("Stale-state recovery failed")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def start_celery_worker_if_configured():
    if not settings.auto_start_celery or settings.app_env == "test":
        return
    from app.core.celery_process import start_celery_worker
    start_celery_worker()


@app.on_event("shutdown")
def stop_celery_worker_if_managed():
    from app.core.celery_process import stop_celery_worker
    stop_celery_worker()


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
@app.get("/ping", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/health", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/ping", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/health/db", tags=["health"])
def health_db() -> dict:
    import time
    from app.db.session import engine
    from sqlalchemy import text

    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"status": "ok", "db_ms": round(elapsed_ms, 1)}
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"status": "error", "db_ms": round(elapsed_ms, 1), "error": str(exc)[:200]}


@app.get("/health/providers", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/health/providers", tags=["health"])
def health_providers() -> dict:
    """Check which LLM providers are configured and available."""
    from app.ai.llm.failover import FailoverLLMProvider

    try:
        failover = FailoverLLMProvider()
        providers = []
        for provider in failover.providers:
            name = getattr(provider, "provider_name", provider.__class__.__name__)
            available = provider.is_available()
            providers.append({
                "name": name,
                "available": available,
                "status": "configured" if available else "not_configured",
            })
        return {
            "status": "ok",
            "providers": providers,
            "active_count": len(failover.available_providers),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
