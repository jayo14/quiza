import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, Request

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.exceptions import RateLimitedError
from app.models.user import User

_WINDOW_SECONDS = 60


class InMemoryRateLimiter:
    """Fixed-window, per-process rate limiter. Good enough for a single-instance
    deployment; swap for a Redis-backed limiter before running multiple workers."""

    def __init__(self, limit_per_minute: int) -> None:
        self._limit = limit_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < _WINDOW_SECONDS]
            if len(recent) >= self._limit:
                raise RateLimitedError(
                    f"Rate limit exceeded: max {self._limit} AI requests per minute."
                )
            recent.append(now)
            self._hits[key] = recent


ai_rate_limiter = InMemoryRateLimiter(settings.ai_rate_limit_per_minute)
_auth_limiter = InMemoryRateLimiter(limit_per_minute=10)


def enforce_ai_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    ai_rate_limiter.check(current_user.id)


def enforce_auth_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    _auth_limiter.check(client_ip)
