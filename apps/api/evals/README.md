# Document Intelligence — RAG evaluation harness

This folder holds a **small, runnable** evaluation toolkit for retrieval + QA against a live API (no mocks).

## Files

| File | Purpose |
| --- | --- |
| `sample_eval_set.json` | Example eval cases (replace UUIDs with your workspace/document ids) |
| `metrics.py` | Pure metric helpers (recall@k, citation checks, keyword overlap, groundedness proxy) |
| `run_eval.py` | CLI runner: logs in, runs `/api/query/ask` with `debug=true`, aggregates scores |

## Prerequisites

- API running (`uvicorn` or docker) with **fake** or real providers configured.
- A user account and at least one **indexed** document for grounded cases.
- Edit `sample_eval_set.json` (or pass `--eval-set`) with real `workspace_id` / optional `document_id`.
- For a known-good indexed text body during local setup, upload `fixtures/demo_document.txt` from the repo root (same content shape the API smoke test uses for fake-embedding alignment).

## Run

From `apps/api` (with dependencies installed):

```bash
python evals/run_eval.py \
  --base-url http://127.0.0.1:8000 \
  --email you@example.com \
  --password yourpassword \
  --eval-set evals/sample_eval_set.json
```

Dry-run (validate JSON only):

```bash
python evals/run_eval.py --eval-set evals/sample_eval_set.json --dry-run
```

## Metrics (interpretation)

- **recall@k**: fraction of `expected_chunk_ids` found in `debug.retrieved_chunk_ids[:k]` (skipped if no expected ids).
- **citation_present**: whether any citations were returned.
- **answerability_match**: compares `message.answerability` to `expect_answerability` when set.
- **keyword_overlap**: substring match rate for `expected_answer_phrases` in the assistant answer.
- **groundedness_proxy**: fraction of longer answer tokens appearing in citation excerpts (rough faithfulness hint).

These are **proxies** for interviews and regression smoke checks, not academic benchmarks.
