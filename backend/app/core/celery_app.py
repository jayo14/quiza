import ssl

from celery import Celery

from app.core.config import settings

broker_use_ssl = None
if settings.redis_url.startswith("rediss://"):
    broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }

celery_app = Celery(
    "quiza",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

if broker_use_ssl:
    celery_app.conf.update(
        broker_use_ssl=broker_use_ssl,
        redis_backend_use_ssl=broker_use_ssl,
    )

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    worker_max_memory_per_child=400000,
    include=["app.tasks"],
)

celery_app.autodiscover_tasks(["app"])

import app.tasks  # noqa: E402, F401
