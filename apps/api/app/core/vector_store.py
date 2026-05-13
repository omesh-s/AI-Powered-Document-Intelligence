from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class VectorRecord:
    chunk_id: UUID
    workspace_id: UUID
    document_id: UUID
    document_version_id: UUID
    embedding: list[float]
    metadata: dict[str, Any]


class VectorStore(ABC):
    """Pluggable vector index (Postgres pgvector, Qdrant, etc.)."""

    @abstractmethod
    async def upsert(self, session: "AsyncSession", records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_for_document_version(
        self, session: "AsyncSession", document_version_id: UUID
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def query_similar(
        self,
        session: "AsyncSession",
        *,
        workspace_id: UUID,
        query_embedding: list[float],
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[UUID, float]]:
        """Return list of (chunk_id, score) ordered best-first."""
        raise NotImplementedError
