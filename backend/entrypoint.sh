#!/bin/bash
set -e

# If called with an explicit command (e.g. "celery ..."), skip migrations and
# exec directly. Only the API server container is responsible for running them.
if [ "$1" = "celery" ]; then
    exec "$@"
fi

echo "[helm] Running database migrations..."
alembic upgrade head

echo "[helm] Starting API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-4}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
