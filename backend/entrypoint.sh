#!/bin/sh
set -e

# Run database migrations
alembic upgrade head

# Start Celery worker in background
celery -A app.core.celery_app worker --loglevel=info --concurrency=2 &

# Start the web server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
