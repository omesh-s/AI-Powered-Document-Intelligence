"""Local demo prep: ensure MinIO bucket exists and print startup checklist.

Run:

    cd apps/api
    python ../scripts/demo_setup.py

Requires the same environment as the API (see ../../.env).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    api = Path(__file__).resolve().parent.parent / "apps" / "api"
    script = api / "scripts" / "ensure_minio_bucket.py"
    print("Ensuring object storage bucket (if S3_ENDPOINT_URL is set)…")
    proc = subprocess.run([sys.executable, str(script)], cwd=api, env={**__import__("os").environ})
    if proc.returncode != 0:
        return proc.returncode
    print()
    print("Next steps:")
    print("  1. docker compose up -d")
    print("  2. cd apps/api && python -m pip install -e \".[dev]\" && python -m alembic upgrade head")
    print("  3. make api   # or: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("  4. make web   # separate terminal")
    print("  5. Register in UI, upload fixtures/demo_document.txt, run ingestion job from Diagnostics")
    print("     or: make smoke  # with API running")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
