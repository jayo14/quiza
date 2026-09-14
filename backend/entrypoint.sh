#!/bin/sh
set -e

# Run database migrations before starting services
alembic upgrade head

# Hand off to supervisord (manages uvicorn + celery with auto-restart)
exec supervisord -c /app/supervisord.conf
