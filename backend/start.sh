#!/usr/bin/env bash
set -euo pipefail

echo "Applying database migrations..."
alembic upgrade head

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A app.core.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# Start FastAPI server
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

cleanup() {
  echo "Shutting down..."
  kill $CELERY_PID 2>/dev/null || true
  kill $API_PID 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Celery PID: $CELERY_PID"
echo "API PID: $API_PID"
echo "Both services running. Press Ctrl+C to stop."

wait
