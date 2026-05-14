# Screenshots (portfolio)

Capture these after a clean local run (`docker compose up -d`, API + web, one indexed document). Store under `docs/screenshots/` (gitignored if you prefer) or attach to your portfolio site.

| File | What to show | Caption idea |
| --- | --- | --- |
| `docs/screenshots/01-login.png` | Login screen | JWT auth entry point |
| `docs/screenshots/02-dashboard.png` | Workspace dashboard | Recent docs and sessions |
| `docs/screenshots/03-documents.png` | Document list with status badges | Lifecycle filter + pagination |
| `docs/screenshots/04-upload.png` | Upload flow mid-step or success | Presigned PUT → finalize |
| `docs/screenshots/05-document-detail.png` | Document detail, pages or chunks tab | Anchors for citation deep links |
| `docs/screenshots/06-query-citations.png` | Query view with citation cards | Grounded answer + scores |
| `docs/screenshots/07-diagnostics.png` | Diagnostics job detail | Ingestion metrics JSON |
| `docs/screenshots/08-mobile-nav.png` | Narrow viewport with drawer open | Responsive workspace shell |

## Demo script (2 minutes)

1. Register / log in, create a workspace.  
2. Upload `fixtures/demo_document.txt`, run ingestion (`python -m app.workers.ingestion_runner <job_id>` or reprocess from UI).  
3. Open Query scoped to the document; ask about the repeated **RISK_ALPHA** clause (matches fake embeddings).  
4. Expand citations and follow a link to chunk anchor on the document page.
