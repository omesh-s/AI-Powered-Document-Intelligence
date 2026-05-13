from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID


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
    async def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_for_document_version(self, document_version_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def query_similar(
        self,
        *,
        workspace_id: UUID,
        query_embedding: list[float],
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[UUID, float]]:
        """Return list of (chunk_id, score)."""
        raise NotImplementedError
