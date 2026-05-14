# Deployment notes

This repository is **portfolio / demo oriented**. A production rollout still requires your own verification (TLS, secrets, backups, scaling, monitoring).

## API container (reference)

Build from the repository root:

```bash
docker build -f apps/api/Dockerfile -t docintel-api:local .
```

Run with environment variables from `.env.example`. Apply **Alembic** migrations from a container or job that has `DATABASE_SYNC_URL` and the `alembic/` tree (same as local `make migrate`).

## Web

The Vite app defaults to **dev proxy** of `/api` → `http://127.0.0.1:8000`. For production, serve static `apps/web` build behind a reverse proxy that routes `/api` to the API origin and sets `API_CORS_ORIGINS` on the API to your real web origin.

## Readiness

- `GET /health` — process up.  
- `GET /ready` — database and (when Celery uses Redis) Redis reachable.

## Startup order (local full stack)

1. `docker compose up -d` (Postgres, Redis, MinIO).  
2. Create MinIO bucket once: `make demo-setup` or `cd apps/api && python scripts/ensure_minio_bucket.py`.  
3. `make migrate` then `make api`.  
4. After each upload: run `python -m app.workers.ingestion_runner <job_id>` until a worker service exists.  
5. `make web`.

## CORS and base URL

- API: `API_CORS_ORIGINS` comma-separated list must include the browser origin (e.g. `http://localhost:5173`).  
- Web dev: `vite.config.ts` proxies `/api`; no `VITE_` base URL required for local demos.
