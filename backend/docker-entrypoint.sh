#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL']
for attempt in range(60):
    try:
        with create_engine(url, pool_pre_ping=True).connect() as conn:
            conn.execute(text('SELECT 1'))
        break
    except Exception as exc:
        if attempt == 59:
            raise
        print(f'Waiting for database ({attempt + 1}/60): {exc}')
        time.sleep(2)
PY
alembic upgrade head
if [ "${SEED_DATA:-false}" = "true" ]; then
  python -m app.seed
fi
exec "$@"
