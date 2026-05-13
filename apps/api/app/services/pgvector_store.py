from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.vector_store import VectorRecord, VectorStore
from app.models.document import Chunk


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


class PgVectorVectorStore(VectorStore):
    """Postgres pgvector similarity search on `chunks.embedding`."""

    async def upsert(self, session: AsyncSession, records: list[VectorRecord]) -> None:
        if not records:
            return
        for rec in records:
            await session.execute(
                update(Chunk)
                .where(Chunk.id == rec.chunk_id)
                .values(embedding=rec.embedding, vector_id=str(rec.chunk_id))
            )

    async def delete_for_document_version(
        self, session: AsyncSession, document_version_id: UUID
    ) -> None:
        await session.execute(
            update(Chunk)
            .where(Chunk.document_version_id == document_version_id)
            .values(embedding=None)
        )

    async def query_similar(
        self,
        session: AsyncSession,
        *,
        workspace_id: UUID,
        query_embedding: list[float],
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[UUID, float]]:
        _ = get_settings()
        mf = metadata_filter or {}
        doc_ver: UUID | None = mf.get("document_version_id")
        doc_id: UUID | None = mf.get("document_id")

        vec_lit = _vector_literal(query_embedding)
        filters = [
            "d.workspace_id = CAST(:ws AS uuid)",
            "c.embedding IS NOT NULL",
            "d.deleted_at IS NULL",
        ]
        params: dict[str, Any] = {
            "ws": str(workspace_id),
            "qemb": vec_lit,
            "lim": int(limit),
        }

        if doc_ver is not None:
            filters.append("dv.id = CAST(:ver AS uuid)")
            params["ver"] = str(doc_ver)
        else:
            filters.append("dv.id = d.latest_version_id")

        if doc_id is not None:
            filters.append("d.id = CAST(:doc AS uuid)")
            params["doc"] = str(doc_id)

        where_sql = " AND ".join(filters)
        sql = text(
            f"""
            SELECT c.id AS chunk_id,
                   GREATEST(0.0, LEAST(1.0, 1.0 - (c.embedding <=> CAST(:qemb AS vector)))) AS score
            FROM chunks c
            INNER JOIN document_versions dv ON dv.id = c.document_version_id
            INNER JOIN documents d ON d.id = dv.document_id
            WHERE {where_sql}
            ORDER BY c.embedding <=> CAST(:qemb AS vector) ASC
            LIMIT :lim
            """
        )
        result = await session.execute(sql, params)
        rows = result.mappings().all()
        return [(UUID(str(r["chunk_id"])), float(r["score"])) for r in rows]


def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_backend == "pgvector":
        return PgVectorVectorStore()
    raise AppError(
        "VECTOR_BACKEND_UNSUPPORTED",
        "Only pgvector is implemented for vector search in this release",
        status_code=501,
        details={"vector_backend": settings.vector_backend},
    )
