from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.vector_store import VectorRecord
from app.models.document import Chunk
from app.services.embedding_providers import get_embedding_provider
from app.services.pgvector_store import get_vector_store


async def embed_texts_batch(texts: list[str]) -> tuple[list[list[float]], str]:
    provider = get_embedding_provider()
    if not texts:
        return [], provider.model_name
    out: list[list[float]] = []
    settings = get_settings()
    batch = max(1, settings.embedding_batch_size)
    for i in range(0, len(texts), batch):
        part = texts[i : i + batch]
        out.extend(await provider.embed_texts(part))
    return out, provider.model_name


async def embed_query_text(text: str) -> tuple[list[float], str]:
    provider = get_embedding_provider()
    vec = await provider.embed_query(text)
    return vec, provider.model_name


async def embed_and_store_chunks(session: AsyncSession, chunks: list[Chunk]) -> None:
    """Compute embeddings for chunk texts, persist on rows, and upsert into the vector store."""
    if not chunks:
        return
    settings = get_settings()
    texts = [c.text for c in chunks]
    vectors, model_name = await embed_texts_batch(texts)

    records: list[VectorRecord] = []

    for ch, emb in zip(chunks, vectors, strict=True):
        meta = ch.metadata_json or {}
        try:
            ws = UUID(str(meta["workspace_id"]))
            did = UUID(str(meta["document_id"]))
            vid = UUID(str(meta["document_version_id"]))
        except (KeyError, ValueError):
            # Fallback: join-loaded paths are expensive here; metadata is always set at ingest.
            raise ValueError("Chunk metadata_json missing workspace/document/version ids") from None
        ch.embedding_model = model_name
        ch.embedding = emb
        records.append(
            VectorRecord(
                chunk_id=ch.id,
                workspace_id=ws,
                document_id=did,
                document_version_id=vid,
                embedding=emb,
                metadata=meta,
            )
        )

    await session.flush()
    store = get_vector_store()
    await store.upsert(session, records)
    _ = settings.vector_backend  # reserved for future backend-specific options
