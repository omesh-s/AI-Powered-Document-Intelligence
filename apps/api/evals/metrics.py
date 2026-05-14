"""Lightweight RAG quality metrics (proxies, not gold-standard benchmarks)."""

from __future__ import annotations

import re
from typing import Any


def recall_at_k(expected_chunk_ids: list[str], retrieved_ids: list[str], *, k: int) -> float:
    """Share of expected chunk ids that appear in the first *k* retrieved ids."""
    if not expected_chunk_ids:
        return 1.0
    head = set(retrieved_ids[:k])
    hits = sum(1 for e in expected_chunk_ids if e in head)
    return hits / len(expected_chunk_ids)


def citation_present(citations: list[dict[str, Any]]) -> bool:
    return len(citations) > 0


def citation_any_expected_page(
    citations: list[dict[str, Any]], expected_pages: list[int] | None
) -> bool | None:
    if not expected_pages:
        return None
    pages = {c.get("page_number") for c in citations if c.get("page_number") is not None}
    return bool(pages.intersection(set(expected_pages)))


def keyword_overlap_score(answer: str, expected_phrases: list[str]) -> float:
    """Token-ish overlap: fraction of expected phrases found as substrings (case-insensitive)."""
    if not expected_phrases:
        return 1.0
    lower = answer.lower()
    hits = sum(1 for p in expected_phrases if p.lower() in lower)
    return hits / len(expected_phrases)


def normalized_token_jaccard(a: str, b: str) -> float:
    """Very rough semantic proxy: Jaccard on word sets."""
    ta = {t for t in re.split(r"\W+", a.lower()) if len(t) > 2}
    tb = {t for t in re.split(r"\W+", b.lower()) if len(t) > 2}
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def answerability_match(actual: str | None, expected: str | None) -> bool | None:
    if expected is None:
        return None
    return (actual or "").lower() == expected.lower()


def groundedness_proxy(answer: str, citation_excerpts: list[str]) -> float:
    """Share of answer significant words (len>3) that appear in at least one citation excerpt."""
    aw = {w for w in re.split(r"\W+", answer.lower()) if len(w) > 3}
    if not aw:
        return 1.0
    pool = " ".join(citation_excerpts).lower()
    covered = sum(1 for w in aw if w in pool)
    return covered / len(aw)
