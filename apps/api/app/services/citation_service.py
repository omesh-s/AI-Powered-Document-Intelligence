from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.services.retrieval_service import RetrievalHit


@dataclass(frozen=True)
class CitationPayload:
    document_id: UUID
    document_name: str
    document_version_id: UUID
    page_number: int | None
    chunk_id: UUID
    excerpt: str
    score: float


def _excerpt(text: str, *, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."


def build_citations(hits: list[RetrievalHit], *, excerpt_max: int = 400) -> list[CitationPayload]:
    out: list[CitationPayload] = []
    for h in hits:
        ch = h.chunk
        doc = ch.document_version.document
        page_num: int | None = ch.page.page_number if ch.page is not None else None
        if page_num is None and ch.metadata_json:
            try:
                page_num = int(ch.metadata_json.get("page_number", 1))
            except (TypeError, ValueError):
                page_num = 1
        out.append(
            CitationPayload(
                document_id=doc.id,
                document_name=doc.filename,
                document_version_id=ch.document_version_id,
                page_number=page_num,
                chunk_id=ch.id,
                excerpt=_excerpt(ch.text, max_len=excerpt_max),
                score=float(h.score),
            )
        )
    return out
