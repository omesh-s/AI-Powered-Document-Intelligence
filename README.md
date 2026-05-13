# AI-Powered Document Intelligence

Production-oriented monorepo for document ingestion, semantic indexing, and citation-grounded question answering.

## Phase 1 — Architecture (frozen for implementation)

### Goals

- **Separation of concerns**: HTTP routes stay thin; services own business logic; workers execute long-running pipelines.
- **Durable artifacts**: uploads land in S3-compatible storage; Postgres holds relational truth; vectors live in Postgres (`pgvector`) behind a `VectorStore` interface so Qdrant can be swapped in later.
- **Contracts**: TypeScript DTOs in `packages/types` mirror Pydantic responses where practical; OpenAPI remains the source of truth for HTTP.

### Repository layout

```
.
├── apps/
│   ├── api/
│   │   ├── alembic/                    # migrations (`versions/` contains baseline schema)
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── deps.py              # shared FastAPI dependencies
│   │   │   │   ├── router.py            # aggregates route modules
│   │   │   │   └── routes/              # thin handlers (ingestion list/detail, query, admin still Phase 4+)
│   │   │   ├── core/                    # config, logging, DB session, errors, storage/vector abstractions
│   │   │   ├── models/                  # SQLAlchemy models + declarative `Base`
│   │   │   └── main.py                  # FastAPI app factory + middleware
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── web/                             # React + Vite (package.json only until Phase 6)
├── packages/
│   └── types/                           # Shared Zod/TS contracts (`@docintel/types`)
├── docker-compose.yml                   # Postgres (pgvector image), Redis, MinIO
├── Makefile
├── .env.example
└── README.md
```

### Backend layering

| Layer | Responsibility |
| --- | --- |
| `app/api/routes/*` | Validation, auth dependencies, delegate to services |
| `app/services/*` | Transactions, orchestration, idempotency rules |
| `app/core/*` | Config, logging, DB session, storage/vector abstractions, errors |
| `app/workers/*` | Celery tasks calling the same services as HTTP (later phases) |

### Data flow (ingestion)

1. Client obtains presigned PUT URL → uploads bytes to object storage.
2. API creates `Document`, `DocumentVersion`, `IngestionJob`; worker downloads object, extracts text/OCR, writes `Page`, `StructuredBlock`, `Chunk`, embeddings, updates status.

### Data flow (query)

1. Embed query → hybrid retrieval (semantic + keyword placeholder) → optional rerank → grounded LLM prompt → `QueryMessage` + `Citation` rows.

### Non-functional defaults

- Structured JSON logs with `request_id` correlation.
- Consistent error envelope (`app/core/errors.py`).
- JWT access + refresh (implemented in Phase 3).

## Local infrastructure

```bash
docker compose up -d
```

Creates Postgres (with pgvector image), Redis, and MinIO. Application processes run on the host via `make api` / `make web` once dependencies are installed.

## Environment

Copy `.env.example` to `.env` and adjust secrets. **Never commit real secrets.**

## API documentation

With the API running: `http://localhost:8000/docs`

## Migrations

```bash
cd apps/api && uv sync && uv run alembic upgrade head
```

## Phase 2 status (foundation)

- **Core**: `Settings`, structured logging, request ID + timing, CORS, SlowAPI, `AppError` + validation + rate-limit handlers, **Starlette `HTTPException` handler** (same JSON error envelope as domain errors).
- **Persistence**: full relational + pgvector schema; migrations under `apps/api/alembic/versions/`.
- **Health**: `GET /health`, `GET /ready` at root.

## Phase 3 — Auth, workspaces, documents (implemented)

### Behavior

- **JWT**: short-lived access tokens and longer-lived refresh tokens (`typ` claim distinguishes them). Refresh re-issues a new pair (rotation-friendly; no server-side refresh revocation store yet).
- **Workspaces**: creating a workspace adds the caller as **owner** via `workspace_members`. Listing returns only workspaces the user belongs to, with **role**.
- **Uploads**: two-step flow only — `POST /api/documents/upload-url` returns a presigned **PUT** URL; client uploads bytes to S3/MinIO; `POST /api/documents` finalizes the row. Object keys are `workspaces/{workspace_id}/users/{user_id}/uploads/{upload_uuid}/{safe_filename}`.
- **Ingestion**: each new document gets `DocumentLifecycleStatus.queued`, a `DocumentVersion` (v1), and an `IngestionJob` with `status=pending`, `stage=queued` (worker processing is Phase 4+).
- **Audit**: `document.created` / `document.deleted` rows in `audit_logs`.
- **Errors**: `AppError`, Pydantic validation, rate limits, and Starlette/FastAPI HTTP errors all return `{ "error": { "code", "message", "details", "requestId" } }`.

### API (Phase 3)

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/auth/register` | email, password, optional full_name |
| POST | `/api/auth/login` | |
| POST | `/api/auth/refresh` | body: `refresh_token` |
| GET | `/api/auth/me` | Bearer access token |
| POST | `/api/workspaces/` | create |
| GET | `/api/workspaces/` | list for current user |
| GET | `/api/workspaces/{id}` | member only |
| POST | `/api/documents/upload-url` | workspace_id, filename, content_type, file_size |
| POST | `/api/documents/` | finalize after client upload |
| GET | `/api/documents/` | query: `workspace_id` (required), `page`, `size` |
| GET | `/api/documents/{id}` | |
| DELETE | `/api/documents/{id}` | soft delete (`deleted_at`) |

### Migrations

Run after pulling Phase 3:

```bash
cd apps/api && python -m alembic upgrade head
```

Adds `users.full_name` (`20260514100000_add_user_full_name.py`).

### Tests

Integration tests need Postgres (e.g. `docker compose up -d postgres`). Envelope-only tests run without a database.

```bash
cd apps/api
python -m pip install -e ".[dev]"
python -m pytest tests/ -q
```

Python **3.12+** is recommended for production; the API is kept compatible with **3.10+** (e.g. `str, Enum` instead of `StrEnum`).

### Install & run API

```bash
cd apps/api
python -m pip install -e ".[dev]"
# copy ../../.env.example to ../../.env — set API_SECRET_KEY (≥32 chars), DATABASE_*, S3_*
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Production readiness checklist

See inline sections above and upcoming README expansion after Phases 7–8: TLS termination, secret rotation, backups, horizontal scaling for workers, observability backends, and abuse controls beyond baseline rate limits.
