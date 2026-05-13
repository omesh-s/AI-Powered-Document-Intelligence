from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings


class Reranker(ABC):
    """Optional second-stage ordering of vector hits."""

    @abstractmethod
    async def rerank(self, *, query: str, hits: list[Any]) -> list[Any]:
        raise NotImplementedError


class NoopReranker(Reranker):
    async def rerank(self, *, query: str, hits: list[Any]) -> list[Any]:
        _ = query
        return list(hits)


class PlaceholderReranker(Reranker):
    """Reserved for a hosted cross-encoder or similar; currently identical to noop."""

    async def rerank(self, *, query: str, hits: list[Any]) -> list[Any]:
        _ = query
        return list(hits)


def get_reranker() -> Reranker:
    settings = get_settings()
    if settings.query_reranking_enabled and settings.reranker_provider == "placeholder":
        return PlaceholderReranker()
    return NoopReranker()
