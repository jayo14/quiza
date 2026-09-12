import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import QuizaError

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.exception_handler(QuizaError)
def handle_quiza_error(request: Request, exc: QuizaError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "The server could not complete the request. Please try again."},
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


_celery_worker_proc = None


@app.on_event("startup")
def start_celery_worker_if_configured():
    global _celery_worker_proc
    if not settings.auto_start_celery or settings.app_env == "test":
        return
    import subprocess
    import sys
    try:
        from app.core.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=0.5)
        ping_res = inspector.ping() if inspector else None
        if ping_res:
            logger.info("Active Celery worker detected.")
            return
    except Exception:
        pass

    try:
        logger.info("Auto-starting Celery worker subprocess...")
        _celery_worker_proc = subprocess.Popen(
            [sys.executable, "-m", "celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Celery worker started with PID %d", _celery_worker_proc.pid)
    except Exception as exc:
        logger.warning("Could not auto-start Celery worker: %s", exc)


@app.on_event("shutdown")
def stop_celery_worker_if_managed():
    global _celery_worker_proc
    if _celery_worker_proc and _celery_worker_proc.poll() is None:
        logger.info("Terminating auto-started Celery worker (PID %d)...", _celery_worker_proc.pid)
        _celery_worker_proc.terminate()
        try:
            _celery_worker_proc.wait(timeout=3)
        except Exception:
            _celery_worker_proc.kill()


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
@app.get("/ping", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/health", tags=["health"])
@app.get(f"{settings.api_v1_prefix}/ping", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
