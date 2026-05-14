# AI-Powered Document Intelligence

Monorepo for **document ingestion**, **pgvector** semantic indexing, and **citation-grounded** Q&A (FastAPI + React). OpenAPI: `http://localhost:8000/docs` when the API is running.

## Quick start

```bash
docker compose up -d
cp .env.example .env    # API_SECRET_KEY (≥32 chars), DATABASE_*, S3_* — match Compose
cd apps/api && python -m pip install -e ".[dev]" && python -m alembic upgrade head
make demo-setup         # MinIO bucket if S3_ENDPOINT_URL is set
make api                # terminal 1
make web                # terminal 2 → http://localhost:5173 (Vite proxies /api → :8000)
```

**Smoke** (API up; MinIO reachable from the API process): `make smoke`

**More:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) · [docs/RESUME_AND_INTERVIEW.md](docs/RESUME_AND_INTERVIEW.md) · [apps/web/README.md](apps/web/README.md) · [apps/api/evals/README.md](apps/api/evals/README.md)

## Demo flow

1. Register → workspace → upload **`fixtures/demo_document.txt`**.  
2. Ingest: `cd apps/api && python -m app.workers.ingestion_runner <ingestion_job_id>`.  
3. When status is **indexed**, use **Query** (optional `?document=<uuid>`). With **fake** embeddings, ask about **RISK_ALPHA** (same as `make smoke`).  
4. Check **citations** and links to `#chunk-…` on the document page.

## What’s in the box

| Area | Notes |
| --- | --- |
| **API** (`apps/api`) | JWT auth, workspaces, presign upload → finalize, ingestion (TXT/DOCX/PDF), jobs + reprocess, retrieval + `/api/query/ask`, sessions, citations, admin diagnostics |
| **Web** (`apps/web`) | Auth, dashboard, documents (filter/status), upload, detail (pages/chunks), query/chat, sessions, diagnostics |
| **Infra** | `docker-compose.yml`: Postgres (pgvector image), Redis, MinIO — apps run on the host via Makefile |
| **Eval** (`apps/api/evals`) | `run_eval.py` + `sample_eval_set.json` — see evals README |
| **CI** | `.github/workflows/ci.yml` — Ruff, pytest (Postgres + Redis), web lint / test / build |

**Architecture:** React (Vite) → FastAPI → Postgres + pgvector + Redis (readiness when Celery URLs use redis) + S3-compatible storage. Ingestion core is `process_ingestion_job`; this repo runs it via **`python -m app.workers.ingestion_runner <job_id>`** (no bundled Celery consumer).

## Repo layout

```
apps/api/     # FastAPI, Alembic, tests, evals/, scripts/smoke_test.py
apps/web/     # React + Vite + TypeScript
packages/types/
fixtures/     # demo_document.txt
```

## Tests & eval

```bash
cd apps/api && python -m pip install -e ".[dev]" && python -m pytest tests -q
cd apps/web && npm ci && npm run lint && npm test && npm run build
cd apps/api && python evals/run_eval.py --eval-set evals/sample_eval_set.json --dry-run
```

Python **3.10+** supported; **3.12+** recommended.

## Known limitations

- Ingestion worker is **CLI/manual** in the default demo path.  
- Retrieval is **vector-first**; hybrid BM25 / streaming answers are not implemented here.  
- **Production** deploy is not verified from this repo alone — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Production checklist (short)

- `API_ENV=production` triggers stricter checks in `app/core/startup_validation.py` (secret, CORS, OpenAI keys when providers are `openai`).  
- Plan TLS, secrets rotation, backups, worker scaling, and observability for real deployments.
