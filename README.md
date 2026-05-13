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

1. Embed query → **pgvector** similarity search over `chunks.embedding` (scoped by workspace / document / version) → optional rerank → grounded LLM prompt → persisted `QuerySession`, `QueryMessage`, and `Citation` rows.

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

## Phase 4 — Ingestion foundation (implemented)

Phase 4 adds a working ingestion pipeline foundation that moves documents from `queued` to `indexed` by parsing source content and persisting `pages`, `structured_blocks`, and `chunks`. It also implements ingestion job orchestration contracts (job lifecycle, reprocess, and status progression) and read-only job visibility endpoints.

### Ingestion endpoints

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/ingestion/jobs` | member-only; supports `workspace_id`, `document_id`, `status`, plus pagination (`page`, `size`) |
| GET | `/api/ingestion/jobs/{id}` | member-only; includes job + document summary + metrics/errors |
| POST | `/api/documents/{document_id}/reprocess` | member-only; enqueues a new ingestion job for `latest_version_id` and clears pages/blocks/chunks for that version |

### Worker / manual job runner

Queued jobs can be processed outside request handlers using:

```bash
cd apps/api
python -m app.workers.ingestion_runner <ingestion_job_id>
```

### Supported ingestion formats in this phase
- **TXT** (`text/plain`): fully implemented end-to-end
- **DOCX** (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`): implemented using `python-docx`
- **PDF** (`application/pdf`): implemented using PyMuPDF native text extraction (page-level), with OCR fallback for empty pages (stubbed OCR provider)
- **OCR fallback**: implemented as an abstraction with a deterministic local stub. OCR is invoked when the extracted page text is empty.
- **Embeddings / vector writes**: real `pgvector` embeddings on `chunks.embedding` (Phase 5). Ingestion calls the embedding service after chunking; reprocess recomputes embeddings for the current version’s chunks.

### Readiness behavior

- `/health` stays lightweight.
- `/ready` checks database connectivity and Redis connectivity when Redis broker/backend are configured via `redis://...`. It returns `503` with `status=not_ready` when critical dependencies are unavailable.

## Phase 5 — Retrieval & citation-grounded QA (implemented)

Phase 5 adds end-to-end **semantic retrieval** over chunk embeddings stored in Postgres (`pgvector`), **grounded answer generation** with **citations**, **query session/message persistence**, and an explicit **insufficient evidence** pathway when retrieval scores are weak or empty.

### Query endpoints

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/query/ask` | Member-only; embeds question, retrieves top‑k chunks (scoped to workspace or one `document_id`), optional rerank (noop by default), generates answer, persists session/messages/citations |
| GET | `/api/query/sessions` | Lists the caller’s sessions; requires `workspace_id`; optional `document_id`, `page`, `size` |
| GET | `/api/query/sessions/{session_id}` | Session detail with ordered messages; assistant rows include `citations` and `debug_json` when stored |

### Request / response (ask)

- **Request** (JSON): `workspace_id`, optional `document_id`, optional `session_id` (continue thread), `question`, optional `debug` (includes retrieval diagnostics, no raw prompts).
- **Response**: `session` (id, workspace_id, nullable `document_id`), `message` (assistant turn with `answerability`: `grounded` \| `insufficient_evidence`), `citations[]` (`document_id`, `document_name`, `document_version_id`, `page_number`, `chunk_id`, `excerpt`, `score`), optional `debug`.

### How embeddings & retrieval work

- **Embeddings**: `EmbeddingProvider` (`fake` default for dev/tests; `openai` when `EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY` is set). Batch embedding runs after ingestion chunking and writes vectors on `Chunk.embedding` plus vector-store upserts (pgvector uses the same column).
- **Retrieval**: query embedding → `PgVectorVectorStore.query_similar` (cosine distance `<=>`, score `1 - distance` clamped to `[0,1]`). SQL joins `chunks` → `document_versions` → `documents`, filters `workspace_id`, optional `document_id`, optional `document_version_id`, and **only the document’s `latest_version_id`** when no explicit version filter is passed (avoids stale versions).
- **Reranking**: `Reranker` abstraction; default `NoopReranker`. `PLACEHOLDER` reranker is a no-op reserved for a future cross-encoder.

### Configuration (environment)

| Variable | Purpose |
| --- | --- |
| `EMBEDDING_PROVIDER` | `fake` (default, deterministic vectors) or `openai` |
| `LLM_PROVIDER` | `fake` (default, deterministic answers for tests) or `openai` |
| `OPENAI_API_KEY` | Required when using OpenAI-backed providers |
| `OPENAI_EMBEDDING_MODEL` / `OPENAI_CHAT_MODEL` | Model names for OpenAI adapters |
| `EMBEDDING_DIMENSION` | Must match the embedding column width (default `1536`) |
| `QUERY_TOP_K_RETRIEVAL` | Vector candidates (default `20`) |
| `QUERY_TOP_K_FINAL_CONTEXT` | Chunks passed to the LLM after rerank/trim (default `5`) |
| `QUERY_MIN_SIMILARITY_SCORE` | Drop hits below this score (default `0.0`) |
| `QUERY_MAX_CONTEXT_CHARS` | Soft cap on combined chunk text (default `12000`) |
| `QUERY_ANSWERABILITY_THRESHOLD` | If `> 0`, max retrieved score below this marks `insufficient_evidence` (default `0.0` = off) |
| `QUERY_RERANKING_ENABLED` / `RERANKER_PROVIDER` | Feature flag + `noop` / `placeholder` |

### pgvector index expectations

For small dev datasets the planner can **sequentially scan** `chunks.embedding`. For production-scale similarity search, create an approximate index after you have representative data volume, for example:

```sql
CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
ON chunks USING hnsw (embedding vector_cosine_ops);
```

Tune `m` / `ef_construction` per pgvector docs and your latency/recall targets.

### Migrations

Run after pulling Phase 5:

```bash
cd apps/api && python -m alembic upgrade head
```

Adds `query_messages.answerability` (`20260515120000_query_message_answerability.py`).

### Deferred to Phase 6

- Rich hybrid retrieval (BM25 / keyword fusion) and eval harnesses.
- Hosted rerankers and multi-modal answers.
- Frontend chat UX and streaming responses.

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
