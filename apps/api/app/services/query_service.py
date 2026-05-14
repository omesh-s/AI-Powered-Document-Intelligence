from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.document import Chunk, Document
from app.models.enums import DocumentLifecycleStatus, QueryMessageRole
from app.models.query import Citation, QueryMessage, QuerySession
from app.models.user import User
from app.schemas.pagination import PaginatedMeta
from app.schemas.query import (
    AskRequest,
    AskResponse,
    CitationResponse,
    QueryDebugPayload,
    QueryMessageResponse,
    QuerySessionDetailResponse,
    QuerySessionListItem,
    QuerySessionListResponse,
    QuerySessionSummary,
)
from app.services import answer_service, citation_service
from app.services.retrieval_service import RetrievalHit, retrieve_for_query
from app.services.workspace_service import require_workspace_member


def _merge_debug(
    *,
    retrieval: dict[str, Any],
    answer_debug: dict[str, object],
    debug: bool,
) -> QueryDebugPayload | None:
    if not debug:
        return None
    raw_chunk_ids = retrieval.get("retrieved_chunk_ids", []) or []
    rid = [str(x) for x in list(raw_chunk_ids)[:48]]
    raw_scores = retrieval.get("raw_scores", []) or []
    rsc = [float(x) for x in list(raw_scores)[:48]]
    raw_selected = retrieval.get("selected_chunk_ids", []) or []
    sid = [str(x) for x in list(raw_selected)[:24]]
    return QueryDebugPayload(
        retrieved_chunk_ids=rid,
        raw_scores=rsc,
        selected_chunk_ids=sid,
        embedding_model=retrieval.get("embedding_model"),
        reranker=retrieval.get("reranker"),
        timings_ms=dict(retrieval.get("timings_ms") or {}),
        llm_path=str(answer_debug.get("path", "")),
    )


def _weak_evidence(settings: Any, hits: list[RetrievalHit]) -> bool:
    if not hits:
        return True
    thr = float(settings.query_answerability_threshold or 0.0)
    if thr <= 0.0:
        return False
    return max(h.score for h in hits) < thr


async def ask(
    session: AsyncSession,
    *,
    actor: User,
    body: AskRequest,
) -> AskResponse:
    settings = get_settings()
    scope_document_id: UUID | None = body.document_id
    document_version_id: UUID | None = None

    async with session.begin():
        await require_workspace_member(session, workspace_id=body.workspace_id, user_id=actor.id)

        if body.document_id is not None:
            doc = await session.get(Document, body.document_id)
            if doc is None or doc.deleted_at is not None:
                raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)
            if doc.workspace_id != body.workspace_id:
                raise AppError(
                    "DOCUMENT_FORBIDDEN",
                    "Document is not in this workspace",
                    status_code=403,
                )
            if doc.status != DocumentLifecycleStatus.INDEXED:
                raise AppError(
                    "DOCUMENT_NOT_READY",
                    "Document is not indexed yet; wait for ingestion to finish",
                    status_code=400,
                )
            document_version_id = doc.latest_version_id

        qs: QuerySession
        if body.session_id is None:
            qs = QuerySession(
                workspace_id=body.workspace_id,
                user_id=actor.id,
                title=(body.question.strip()[:512] if body.question.strip() else None),
                scope_document_id=scope_document_id,
            )
            session.add(qs)
            await session.flush()
        else:
            loaded = await session.get(QuerySession, body.session_id)
            if loaded is None:
                raise AppError(
                    "QUERY_SESSION_NOT_FOUND", "Query session not found", status_code=404
                )
            if loaded.user_id != actor.id:
                raise AppError(
                    "QUERY_SESSION_FORBIDDEN",
                    "Not allowed to use this session",
                    status_code=403,
                )
            if loaded.workspace_id != body.workspace_id:
                raise AppError(
                    "QUERY_SESSION_WORKSPACE_MISMATCH",
                    "Session belongs to a different workspace",
                    status_code=400,
                )
            if loaded.scope_document_id != scope_document_id:
                raise AppError(
                    "QUERY_SESSION_SCOPE_MISMATCH",
                    "Session document scope does not match this request",
                    status_code=400,
                )
            qs = loaded

        user_msg = QueryMessage(
            session_id=qs.id,
            role=QueryMessageRole.USER,
            content=body.question.strip(),
        )
        session.add(user_msg)
        await session.flush()

        hits, diag = await retrieve_for_query(
            session,
            workspace_id=body.workspace_id,
            question=body.question,
            document_id=body.document_id,
            document_version_id=document_version_id if body.document_id else None,
        )

        insufficient = _weak_evidence(settings, hits)
        ans = await answer_service.generate_answer(
            question=body.question,
            context_hits=hits,
            insufficient_evidence=insufficient,
        )

        citations_payload = (
            [] if insufficient else citation_service.build_citations(hits, excerpt_max=400)
        )

        debug_payload = _merge_debug(retrieval=diag, answer_debug=ans.llm_debug, debug=body.debug)
        assistant_debug: dict[str, Any] | None = None
        if body.debug:
            full_ids = diag.get("retrieved_chunk_ids", []) or []
            raw_ids = [str(x) for x in list(full_ids)[:48]]
            raw_sc = [float(x) for x in list(diag.get("raw_scores", []) or [])[:48]]
            raw_sel = diag.get("selected_chunk_ids", []) or []
            assistant_debug = {
                "retrieval": {
                    "retrieved_chunk_ids": raw_ids,
                    "raw_scores": raw_sc,
                    "selected_chunk_ids": [str(x) for x in list(raw_sel)[:24]],
                    "embedding_model": diag.get("embedding_model"),
                    "reranker": diag.get("reranker"),
                    "timings_ms": diag.get("timings_ms", {}),
                    "truncated_lists": len(raw_ids) < len(full_ids),
                },
                "answer": ans.llm_debug,
            }

        assistant = QueryMessage(
            session_id=qs.id,
            role=QueryMessageRole.ASSISTANT,
            content=ans.text,
            answerability=ans.answerability,
            debug_json=assistant_debug,
        )
        session.add(assistant)
        await session.flush()

        for cit in citations_payload:
            session.add(
                Citation(
                    query_message_id=assistant.id,
                    document_id=cit.document_id,
                    document_version_id=cit.document_version_id,
                    page_number=int(cit.page_number or 1),
                    chunk_id=cit.chunk_id,
                    quote_text=cit.excerpt,
                    score=cit.score,
                )
            )

        await session.flush()

    return AskResponse(
        session=QuerySessionSummary(
            id=qs.id,
            workspace_id=qs.workspace_id,
            document_id=qs.scope_document_id,
        ),
        message=QueryMessageResponse(
            id=assistant.id,
            role="assistant",
            content=ans.text,
            answerability=ans.answerability,
        ),
        citations=[
            CitationResponse(
                document_id=c.document_id,
                document_name=c.document_name,
                document_version_id=c.document_version_id,
                page_number=c.page_number,
                chunk_id=c.chunk_id,
                excerpt=c.excerpt,
                score=c.score,
            )
            for c in citations_payload
        ],
        debug=debug_payload,
    )


async def list_sessions(
    session: AsyncSession,
    *,
    actor: User,
    workspace_id: UUID,
    document_id: UUID | None,
    page: int,
    size: int,
) -> QuerySessionListResponse:
    await require_workspace_member(session, workspace_id=workspace_id, user_id=actor.id)

    filters = [
        QuerySession.user_id == actor.id,
        QuerySession.workspace_id == workspace_id,
    ]
    if document_id is not None:
        filters.append(QuerySession.scope_document_id == document_id)

    count_stmt = select(func.count()).select_from(QuerySession).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    stmt = (
        select(QuerySession)
        .where(*filters)
        .order_by(QuerySession.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await session.execute(stmt)).scalars().all()

    items = [
        QuerySessionListItem(
            id=r.id,
            workspace_id=r.workspace_id,
            document_id=r.scope_document_id,
            title=r.title,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return QuerySessionListResponse(
        items=items,
        pagination=PaginatedMeta(page=page, size=size, total=total),
    )


async def get_session_detail(
    session: AsyncSession,
    *,
    actor: User,
    session_id: UUID,
) -> QuerySessionDetailResponse:
    stmt = (
        select(QuerySession)
        .where(QuerySession.id == session_id)
        .options(
            selectinload(QuerySession.messages)
            .selectinload(QueryMessage.citations)
            .selectinload(Citation.document),
            selectinload(QuerySession.messages)
            .selectinload(QueryMessage.citations)
            .selectinload(Citation.chunk)
            .selectinload(Chunk.page),
        )
    )
    qs = (await session.execute(stmt)).scalar_one_or_none()
    if qs is None:
        raise AppError("QUERY_SESSION_NOT_FOUND", "Query session not found", status_code=404)
    await require_workspace_member(session, workspace_id=qs.workspace_id, user_id=actor.id)
    if qs.user_id != actor.id:
        raise AppError(
            "QUERY_SESSION_FORBIDDEN", "Not allowed to view this session", status_code=403
        )

    messages_out: list[QueryMessageResponse] = []
    for m in sorted(qs.messages, key=lambda x: x.created_at):
        cites: list[CitationResponse] | None = None
        if m.role == QueryMessageRole.ASSISTANT and m.citations:
            cites = []
            for c in m.citations:
                page_num = int(c.page_number)
                if c.chunk is not None and c.chunk.page is not None:
                    page_num = c.chunk.page.page_number
                cites.append(
                    CitationResponse(
                        document_id=c.document_id,
                        document_name=c.document.filename,
                        document_version_id=c.document_version_id,
                        page_number=page_num,
                        chunk_id=c.chunk_id,
                        excerpt=(c.quote_text or "")[:2000],
                        score=float(c.score or 0.0),
                    )
                )
        messages_out.append(
            QueryMessageResponse(
                id=m.id,
                role=m.role.value,
                content=m.content,
                answerability=m.answerability,
                created_at=m.created_at,
                citations=cites,
                debug_json=m.debug_json if m.role == QueryMessageRole.ASSISTANT else None,
            )
        )

    return QuerySessionDetailResponse(
        session=QuerySessionSummary(
            id=qs.id,
            workspace_id=qs.workspace_id,
            document_id=qs.scope_document_id,
        ),
        messages=messages_out,
    )
