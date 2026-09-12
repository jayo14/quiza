import atexit
import logging
import subprocess
import sys
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

_celery_proc: subprocess.Popen | None = None


def is_celery_worker_running(timeout: float = 0.5) -> bool:
    """Check if at least one Celery worker is currently active and pingable."""
    try:
        inspector = celery_app.control.inspect(timeout=timeout)
        ping_dict = inspector.ping() if inspector else None
        return bool(ping_dict)
    except Exception:
        return False


def _set_pdeathsig():
    """Ensure child Celery worker is killed when parent process dies (Linux only)."""
    try:
        import ctypes
        import signal

        PR_SET_PDEATHSIG = 1
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    except Exception:
        pass


def start_celery_worker() -> subprocess.Popen | None:
    """Start Celery worker in a subprocess if not already running."""
    global _celery_proc

    if not getattr(settings, "auto_start_celery", True):
        logger.info("Celery auto-start is disabled via settings.")
        return None

    if _celery_proc is not None and _celery_proc.poll() is None:
        logger.info("Celery worker subprocess is already running (PID: %d).", _celery_proc.pid)
        return _celery_proc

    # Check if an external Celery worker is already running
    if is_celery_worker_running():
        logger.info("Active Celery worker detected on message broker. Subprocess start skipped.")
        return None

    # Check Redis connectivity
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception as exc:
        logger.warning(
            "Redis is not reachable at %s (%s). Celery worker could not be started.",
            settings.redis_url,
            exc,
        )
        return None

    backend_dir = Path(__file__).resolve().parent.parent.parent
    cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.core.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
    ]

    try:
        logger.info("Starting background Celery worker subprocess...")
        _celery_proc = subprocess.Popen(
            cmd,
            cwd=str(backend_dir),
            preexec_fn=_set_pdeathsig if sys.platform.startswith("linux") else None,
        )
        logger.info("Celery worker started successfully (PID: %d).", _celery_proc.pid)
        atexit.register(stop_celery_worker)
        return _celery_proc
    except Exception as exc:
        logger.exception("Failed to start Celery worker subprocess: %s", exc)
        return None


def stop_celery_worker() -> None:
    """Cleanly terminate Celery worker subprocess if managed by this process."""
    global _celery_proc
    if _celery_proc is not None and _celery_proc.poll() is None:
        logger.info("Shutting down Celery worker subprocess (PID: %d)...", _celery_proc.pid)
        try:
            _celery_proc.terminate()
            _celery_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Celery worker PID %d did not terminate gracefully; killing.", _celery_proc.pid)
            _celery_proc.kill()
            _celery_proc.wait(timeout=2)
        except Exception as exc:
            logger.warning("Error stopping Celery worker: %s", exc)
        finally:
            _celery_proc = None
        logger.info("Celery worker shutdown complete.")
