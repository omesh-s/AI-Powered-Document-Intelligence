from __future__ import annotations

import hashlib
import math
import struct
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


class EmbeddingProvider(ABC):
    """Swappable text embedding provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text (same order)."""

    async def embed_query(self, text: str) -> list[float]:
        vecs = await self.embed_texts([text])
        return vecs[0]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, normalized vectors for tests and local dev without API keys."""

    def __init__(self, *, dimension: int, model_name: str = "fake-embedding-v1") -> None:
        self._dim = dimension
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def _single(self, text: str) -> list[float]:
        out: list[float] = []
        cur = hashlib.sha256(text.encode("utf-8")).digest()
        while len(out) < self._dim:
            cur = hashlib.sha256(cur + text.encode("utf-8", errors="replace")).digest()
            for j in range(0, len(cur) - 3, 4):
                v = struct.unpack(">i", cur[j : j + 4])[0] / (2**31)
                out.append(max(-1.0, min(1.0, float(v))))
                if len(out) >= self._dim:
                    break
        out = out[: self._dim]
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        return [x / norm for x in out]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._single(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings API (requires OPENAI_API_KEY)."""

    def __init__(self, *, api_key: str, model: str, dimension: int) -> None:
        self._api_key = api_key
        self._model = model
        self._dim = dimension

    @property
    def model_name(self) -> str:
        return self._model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload: dict[str, Any] = {"model": self._model, "input": texts}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise AppError(
                "EMBEDDING_PROVIDER_ERROR",
                "Embedding provider request failed",
                status_code=502,
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        data = resp.json()
        rows = sorted(data["data"], key=lambda d: d["index"])
        vectors = [r["embedding"] for r in rows]
        for v in vectors:
            if len(v) != self._dim:
                raise AppError(
                    "EMBEDDING_DIMENSION_MISMATCH",
                    "Embedding dimension does not match configured EMBEDDING_DIMENSION",
                    status_code=500,
                    details={"expected": self._dim, "got": len(v)},
                )
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise AppError(
                "EMBEDDING_NOT_CONFIGURED",
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai",
                status_code=503,
            )
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )
    return FakeEmbeddingProvider(dimension=settings.embedding_dimension, model_name="fake-embedding-v1")
