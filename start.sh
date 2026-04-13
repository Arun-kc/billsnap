#!/bin/sh
set -e

echo "=== BillSnap startup ==="
echo "PORT=$PORT"
echo "APP_ENV=$APP_ENV"

echo "--- Running Alembic migrations ---"
alembic upgrade head

echo "--- Starting uvicorn on port $PORT ---"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info
