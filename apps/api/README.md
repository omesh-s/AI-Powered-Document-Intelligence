# docintel-api

FastAPI service for the Document Intelligence platform.

## Setup

```bash
cd apps/api
uv sync
cp ../../.env.example ../../.env   # or copy into apps/api — load from repo root in dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Configure `DATABASE_URL` for `asyncpg` and `DATABASE_SYNC_URL` for Alembic (psycopg3 sync).
