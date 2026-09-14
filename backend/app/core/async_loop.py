import asyncio
import logging

logger = logging.getLogger(__name__)

_worker_loop: asyncio.AbstractEventLoop | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """Return a shared event loop for the Celery worker process.

    Reuses one loop across tasks to avoid creating/destroying loops (and their
    underlying httpx connection pools) on every Celery task. The loop is created
    lazily on first access and kept alive for the worker's lifetime.
    """
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.info("Created shared Celery worker event loop.")
    return _worker_loop


def run_async(coro):
    """Run an async coroutine on the shared worker event loop from sync Celery code."""
    loop = get_worker_loop()
    return loop.run_until_complete(coro)
