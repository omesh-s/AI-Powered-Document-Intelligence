# Resume and interview notes

Concise, factual bullets aligned with this repository (adjust titles/dates for your CV).

## Resume bullets

- Built a **FastAPI + Postgres (pgvector)** document intelligence API with **presigned S3 uploads**, **ingestion pipeline** (TXT/DOCX/PDF), **semantic retrieval**, and **citation-grounded QA** with session persistence.  
- Implemented a **React + Vite** console with auth, workspace routing, document lifecycle UI, query/chat with citations, diagnostics, and **Vitest** component coverage.  
- Added **deterministic fake embedding/LLM providers** for offline CI, plus optional OpenAI adapters behind configuration.  
- Shipped **smoke automation** (`apps/api/scripts/smoke_test.py`) and **GitHub Actions** CI (Ruff, pytest with Postgres/Redis, web lint/test/build).

## Technical talking points

- Separation of **routes vs services vs workers**; ingestion executed via `process_ingestion_job` shared by CLI runner and tests.  
- **pgvector** cosine retrieval scoped by workspace and latest document version to avoid stale chunks.  
- **Two-phase upload** (presign PUT → finalize) with workspace-scoped object keys and audit logging.  
- **JWT access + refresh** with refresh-on-401 in the web client.  
- **Insufficient evidence** path when retrieval scores are weak (`QUERY_ANSWERABILITY_THRESHOLD`).  
- **Structured JSON logging** and consistent `AppError` HTTP envelope with request IDs.  
- **Alembic** migrations and Docker Compose for local dependencies (not full app stack in Compose by default).

## Engineering decisions

- **Fake providers** default for zero-cost demos and CI; swap to OpenAI via env only.  
- **Ingestion worker** invoked explicitly (`ingestion_runner`) instead of coupling long runs into HTTP handlers—clear ops boundary, tradeoff: extra step for demos.  
- **Truncated retrieval debug** lists in API responses to avoid oversized payloads in `debug_json`.

## Tradeoffs and next steps

- **No Celery service in repo yet**—horizontal worker scaling left as future work.  
- **Vector-only retrieval**—no hybrid BM25 in this codebase.  
- **Production Docker image** is a reference Dockerfile; cloud deploy not verified from this repo alone.
