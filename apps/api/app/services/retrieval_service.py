from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.document import Chunk, DocumentVersion
from app.services.embedding_service import embed_query_text
from app.services.pgvector_store import get_vector_store
from app.services.reranking_service import get_reranker


@dataclass(frozen=True)
class RetrievalHit:
    chunk: Chunk
    score: float
    vector_rank: int


async def _load_chunks_ordered(session: AsyncSession, ids_ordered: list[UUID]) -> dict[UUID, Chunk]:
    if not ids_ordered:
        return {}
    stmt = (
        select(Chunk)
        .where(Chunk.id.in_(ids_ordered))
        .options(
            selectinload(Chunk.document_version).selectinload(DocumentVersion.document),
            selectinload(Chunk.page),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {c.id: c for c in rows}


def _trim_by_max_chars(hits: list[RetrievalHit], max_chars: int) -> list[RetrievalHit]:
    out: list[RetrievalHit] = []
    used = 0
    for h in hits:
        t = h.chunk.text or ""
        if used + len(t) > max_chars and out:
            break
        out.append(h)
        used += len(t)
    return out or hits[:1]


async def retrieve_for_query(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    question: str,
    document_id: UUID | None = None,
    document_version_id: UUID | None = None,
) -> tuple[list[RetrievalHit], dict[str, Any]]:
    settings = get_settings()
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    query_embedding, emb_model = await embed_query_text(question)
    timings["embed_query_ms"] = (time.perf_counter() - t0) * 1000

    metadata_filter: dict[str, Any] = {"workspace_id": str(workspace_id)}
    if document_id is not None:
        metadata_filter["document_id"] = document_id
    if document_version_id is not None:
        metadata_filter["document_version_id"] = document_version_id

    t1 = time.perf_counter()
    store = get_vector_store()
    raw = await store.query_similar(
        session,
        workspace_id=workspace_id,
        query_embedding=query_embedding,
        limit=settings.query_top_k_retrieval,
        metadata_filter=metadata_filter,
    )
    timings["vector_search_ms"] = (time.perf_counter() - t1) * 1000

    retrieved_ids = [cid for cid, _ in raw]
    raw_scores = [float(s) for _, s in raw]

    by_id = await _load_chunks_ordered(session, retrieved_ids)
    hits: list[RetrievalHit] = []
    for rank, (cid, score) in enumerate(raw, start=1):
        ch = by_id.get(cid)
        if ch is None:
            continue
        hits.append(RetrievalHit(chunk=ch, score=float(score), vector_rank=rank))

    filtered = [h for h in hits if h.score >= settings.query_min_similarity_score]

    t2 = time.perf_counter()
    reranker = get_reranker()
    reranked = await reranker.rerank(query=question, hits=filtered)
    timings["rerank_ms"] = (time.perf_counter() - t2) * 1000

    final = reranked[: settings.query_top_k_final_context]
    final = _trim_by_max_chars(final, settings.query_max_context_chars)

    selected_ids = [h.chunk.id for h in final]

    diagnostics: dict[str, Any] = {
        "retrieved_chunk_ids": [str(x) for x in retrieved_ids],
        "raw_scores": raw_scores,
        "selected_chunk_ids": [str(x) for x in selected_ids],
        "embedding_model": emb_model,
        "reranker": reranker.__class__.__name__,
        "timings_ms": timings,
    }
    return final, diagnostics
