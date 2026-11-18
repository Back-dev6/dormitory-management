#!/bin/sh
set -e

echo "[entrypoint] Chạy migration..."
alembic upgrade head

if [ "$SEED_DEMO_DATA" = "true" ]; then
  echo "[entrypoint] Nạp dữ liệu mẫu (SEED_DEMO_DATA=true)..."
  python -m app.db.seed
fi

exec "$@"
