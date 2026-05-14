#!/usr/bin/env python3
"""Run eval cases against a live Document Intelligence API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from evals import metrics as M

DEFAULT_EVAL = Path(__file__).resolve().parent / "sample_eval_set.json"


def _load_cases(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "cases" not in data or not isinstance(data["cases"], list):
        raise SystemExit("eval set must contain a 'cases' array")
    return data


def _login(client: httpx.Client, base: str, email: str, password: str) -> str:
    r = client.post(f"{base}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise SystemExit(f"login failed: {r.status_code} {r.text[:500]}")
    return str(r.json()["tokens"]["access_token"])


def _ask(
    client: httpx.Client,
    base: str,
    token: str,
    *,
    workspace_id: str,
    document_id: str | None,
    question: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "workspace_id": workspace_id,
        "question": question,
        "debug": True,
    }
    if document_id:
        body["document_id"] = document_id
    r = client.post(
        f"{base}/api/query/ask",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=120.0,
    )
    if r.status_code != 200:
        raise SystemExit(f"ask failed: {r.status_code} {r.text[:800]}")
    return r.json()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="API origin without trailing slash")
    p.add_argument("--email", default="", help="User email (required unless --dry-run)")
    p.add_argument("--password", default="", help="User password (required unless --dry-run)")
    p.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL, help="Path to eval JSON")
    p.add_argument("--k", type=int, default=10, help="k for recall@k")
    p.add_argument("--dry-run", action="store_true", help="Only validate eval set JSON")
    args = p.parse_args()
    base = args.base_url.rstrip("/")

    data = _load_cases(args.eval_set)
    cases = data["cases"]
    print(f"Loaded {len(cases)} case(s) from {args.eval_set}")
    if args.dry_run:
        print("Dry run OK")
        return

    if not args.email or not args.password:
        raise SystemExit("--email and --password required (or use --dry-run)")

    summary: list[dict[str, Any]] = []
    with httpx.Client() as client:
        token = _login(client, base, args.email, args.password)
        for c in cases:
            cid = c["id"]
            wid = str(c["workspace_id"])
            did = c.get("document_id")
            did_str = str(did) if did else None
            question = str(c["question"])
            out = _ask(client, base, token, workspace_id=wid, document_id=did_str, question=question)
            msg = out.get("message", {})
            cites = out.get("citations") or []
            dbg = out.get("debug") or {}
            retrieved = [str(x) for x in dbg.get("retrieved_chunk_ids", [])]
            expected = [str(x) for x in c.get("expected_chunk_ids", [])]
            recall = M.recall_at_k(expected, retrieved, k=args.k) if expected else None
            row = {
                "id": cid,
                "recall_at_k": recall,
                "citation_present": M.citation_present(cites),
                "citation_page_match": M.citation_any_expected_page(
                    cites, c.get("expected_pages") or None
                ),
                "answerability_match": M.answerability_match(
                    msg.get("answerability"), c.get("expect_answerability")
                ),
                "keyword_overlap": M.keyword_overlap_score(
                    str(msg.get("content", "")),
                    list(c.get("expected_answer_phrases") or []),
                ),
                "groundedness_proxy": M.groundedness_proxy(
                    str(msg.get("content", "")),
                    [str(x.get("excerpt", "")) for x in cites],
                ),
            }
            summary.append(row)
            print(json.dumps({"case": cid, "metrics": row}, indent=2))

    agg = {
        "cases": len(summary),
        "mean_keyword_overlap": sum(s["keyword_overlap"] for s in summary) / max(len(summary), 1),
        "mean_groundedness_proxy": sum(s["groundedness_proxy"] for s in summary) / max(len(summary), 1),
    }
    recalls = [s["recall_at_k"] for s in summary if s["recall_at_k"] is not None]
    if recalls:
        agg["mean_recall_at_k"] = sum(recalls) / len(recalls)
    print("\n=== aggregate ===\n" + json.dumps(agg, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
