"""HTTP smoke test against a running API + real MinIO (local demo stack).

Steps: /ready → register → workspace → presign → PUT object → finalize →
run ingestion worker subprocess → poll document INDEXED → /query/ask with citations.

Usage (API already running, infra from docker compose, .env loaded):

    cd apps/api
    python scripts/smoke_test.py

Environment:

    SMOKE_API_BASE   default http://127.0.0.1:8000
    SMOKE_FIXTURE    path to demo .txt (default: repo fixtures/demo_document.txt)
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx

# Question aligned with fake embeddings (see tests/test_phase5_query.py).
DEMO_QUESTION = " ".join(["RISK_ALPHA"] * 35)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fixture_bytes() -> bytes:
    custom = (os.environ.get("SMOKE_FIXTURE") or "").strip()
    path = Path(custom) if custom else _repo_root() / "fixtures" / "demo_document.txt"
    if not path.is_file():
        raise SystemExit(f"Fixture not found: {path}")
    return path.read_bytes()


def _die(msg: str, resp: httpx.Response | None = None) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    if resp is not None:
        print(resp.text[:2000], file=sys.stderr)
    raise SystemExit(1)


def _api(base: str, path: str) -> str:
    p = path if path.startswith("/") else f"/{path}"
    return f"{base.rstrip('/')}{p}"


def main() -> int:
    base = (os.environ.get("SMOKE_API_BASE") or "http://127.0.0.1:8000").rstrip("/")
    content = _fixture_bytes()
    checksum = hashlib.sha256(content).hexdigest()

    with httpx.Client(timeout=60.0) as client:
        r = client.get(_api(base, "/ready"))
        if r.status_code != 200:
            _die(f"/ready returned {r.status_code}", r)
        body = r.json()
        if body.get("status") != "ready":
            _die(f"/ready not ready: {body}", r)

        email = f"smoke_{int(time.time())}_{os.getpid()}@example.com"
        password = "smoke-test-pass-9chars-min"
        r = client.post(
            _api(base, "/api/auth/register"),
            json={"email": email, "password": password, "full_name": "Smoke Bot"},
        )
        if r.status_code not in (200, 201):
            _die(f"register {r.status_code}", r)
        token = r.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            _api(base, "/api/workspaces/"), headers=headers, json={"name": "Smoke Workspace"}
        )
        if r.status_code not in (200, 201):
            _die(f"workspace create {r.status_code}", r)
        workspace_id = r.json()["id"]

        r = client.post(
            _api(base, "/api/documents/upload-url"),
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "filename": "demo_smoke.txt",
                "content_type": "text/plain",
                "file_size": len(content),
            },
        )
        if r.status_code != 200:
            _die(f"upload-url {r.status_code}", r)
        up = r.json()
        upload_url = up["upload_url"]
        storage_key = up["storage_key"]
        req_headers = dict(up.get("required_headers") or {})
        put = client.put(upload_url, content=content, headers=req_headers)
        if put.status_code not in (200, 204):
            _die(f"PUT to storage {put.status_code}", put)

        r = client.post(
            _api(base, "/api/documents/"),
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "filename": "demo_smoke.txt",
                "content_type": "text/plain",
                "file_size": len(content),
                "storage_key": storage_key,
                "checksum_sha256": checksum,
                "metadata": {"source": "smoke_test"},
            },
        )
        if r.status_code not in (200, 201):
            _die(f"finalize document {r.status_code}", r)
        doc = r.json()
        document_id = doc["id"]
        job = doc.get("ingestion_job") or {}
        job_id = job.get("id")
        if not job_id:
            _die("no ingestion_job.id on document response", r)

    api_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "app.workers.ingestion_runner", str(job_id)],
        cwd=api_dir,
        env={**os.environ},
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        _die(f"ingestion_runner exit {proc.returncode}")

    deadline = time.time() + 120
    status = ""
    with httpx.Client(timeout=30.0) as client:
        while time.time() < deadline:
            r = client.get(_api(base, f"/api/documents/{document_id}"), headers=headers)
            if r.status_code != 200:
                _die(f"get document {r.status_code}", r)
            status = r.json().get("status", "")
            if status == "indexed":
                break
            if status == "failed":
                _die("document ingestion failed")
            time.sleep(0.75)
        else:
            _die(f"timeout waiting for indexed, last status={status!r}")

        r = client.post(
            _api(base, "/api/query/ask"),
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "document_id": document_id,
                "question": DEMO_QUESTION,
                "debug": False,
            },
        )
        if r.status_code != 200:
            _die(f"ask {r.status_code}", r)
        out = r.json()
        cites = out.get("citations") or []
        if len(cites) < 1:
            _die(f"expected citations, got {out}")
        if out.get("message", {}).get("answerability") != "grounded":
            _die(f"expected grounded answer, got {out.get('message')}")
        doc_uuid = UUID(document_id)
        for c in cites:
            if UUID(str(c["document_id"])) != doc_uuid:
                _die("citation document_id mismatch")

    print("OK: auth, upload/finalize, ingestion, query, citations verified.")
    print(f"    workspace_id={workspace_id} document_id={document_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
