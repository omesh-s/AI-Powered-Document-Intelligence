from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.storage import ObjectStorageClient
from app.models.document import Chunk, Document, DocumentVersion, Page, StructuredBlock
from app.models.enums import (
    DocumentLifecycleStatus,
    IngestionJobStatus,
    PageExtractionMethod,
    StructuredBlockType,
)
from app.models.ingestion import IngestionJob
from app.models.workspace import WorkspaceMember
from app.schemas.ingestion import DocumentIngestionSummary, IngestionJobSummary
from app.services import audit_service
from app.services.workspace_service import require_workspace_member

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExtractedBlock:
    block_type: StructuredBlockType
    text: str
    order_index: int
    level: int | None = None
    content_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    extraction_method: PageExtractionMethod
    raw_text: str
    markdown_text: str
    blocks: list[ExtractedBlock]
    ocr_confidence: float | None = None


class OCRProvider(ABC):
    @abstractmethod
    async def ocr_empty_page(self) -> tuple[str, float | None]:
        """OCR fallback contract for pages without native text."""


class StubOCRProvider(OCRProvider):
    async def ocr_empty_page(self) -> tuple[str, float | None]:
        # Deterministic local stub; replace with a real provider in Phase 5.
        return "OCR_TEXT_STUB", 0.0


class NoopVectorIndexWriter:
    async def index_chunks(self, *, chunks: list[Chunk]) -> None:
        # In Phase 4 we keep embeddings/vector writes as a contract stub.
        # Retrieval indexing becomes fully real in Phase 5.
        _ = chunks
        return


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _job_to_summary(job: IngestionJob) -> IngestionJobSummary:
    return IngestionJobSummary(
        id=job.id,
        document_id=job.document_id,
        document_version_id=job.document_version_id,
        status=job.status.value,
        stage=job.stage,
        progress=float(job.progress),
        attempts=job.attempts,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )


def _doc_to_summary(doc: Document) -> DocumentIngestionSummary:
    return DocumentIngestionSummary(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        status=doc.status.value,
        workspace_id=doc.workspace_id,
        created_at=doc.created_at,
    )


async def create_queued_ingestion_job(
    session: AsyncSession,
    *,
    document_id: UUID,
    document_version_id: UUID,
) -> IngestionJob:
    job = IngestionJob(
        document_id=document_id,
        document_version_id=document_version_id,
        status=IngestionJobStatus.PENDING,
        stage="queued",
        progress=0,
        attempts=0,
    )
    session.add(job)
    await session.flush()
    return job


def _detect_format(document: Document) -> str:
    ct = (document.content_type or "").lower()
    if ct.startswith("text/plain"):
        return "txt"
    if ct.startswith("application/pdf"):
        return "pdf"
    if "wordprocessingml.document" in ct:
        return "docx"
    raise AppError(
        "UNSUPPORTED_MEDIA_TYPE",
        "This file type is not supported for ingestion",
        status_code=415,
        details={"content_type": document.content_type},
    )


def _estimate_token_count(text: str) -> int:
    # Rough heuristic: 1 token ~ 4 chars (English-ish).
    return max(0, int(len(text) / 4))


def _chunk_text(text: str, *, max_chars: int, min_chars: int, overlap_chars: int) -> list[str]:
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end].strip()
        if chunk:
            if len(chunk) < min_chars and end != len(text) and chunks:
                # If the tail is too small, prefer appending it.
                prev = chunks[-1] + "\n\n" + chunk
                chunks[-1] = prev.strip()
            else:
                chunks.append(chunk)
        if end >= len(text):
            break
        # overlap: back up overlap_chars from the next start
        start = max(end - overlap_chars, 0)
        if chunks and start <= (len(chunks[-1]) if chunks else 0):
            # Ensure we always advance (avoid infinite loops with tiny overlap)
            start = end
    return chunks


async def create_reprocess_job(
    session: AsyncSession,
    *,
    actor: Any,
    document_id: UUID,
) -> tuple[IngestionJobSummary, DocumentIngestionSummary]:
    from app.models.document import Document as DocumentModel

    doc = await session.get(DocumentModel, document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)

    await require_workspace_member(
        session,
        workspace_id=doc.workspace_id,
        user_id=actor.id,
    )

    if doc.latest_version_id is None:
        raise AppError(
            "DOCUMENT_HAS_NO_VERSION",
            "Document has no version to reprocess",
            status_code=400,
        )

    latest_version_id = doc.latest_version_id

    async with session.begin():
        # Clear artifacts for this version so we do not leak previous chunks/pages.
        await session.execute(delete(Chunk).where(Chunk.document_version_id == latest_version_id))
        await session.execute(delete(Page).where(Page.document_version_id == latest_version_id))

        doc.status = DocumentLifecycleStatus.QUEUED

        job = await create_queued_ingestion_job(
            session,
            document_id=doc.id,
            document_version_id=latest_version_id,
        )

        await audit_service.record_audit(
            session,
            workspace_id=doc.workspace_id,
            user_id=actor.id,
            action="document.reprocess_queued",
            resource_type="document",
            resource_id=doc.id,
            metadata={"ingestion_job_id": str(job.id)},
        )

    await session.refresh(job)
    return _job_to_summary(job), _doc_to_summary(doc)


async def _clear_version_artifacts(session: AsyncSession, *, document_version_id: UUID) -> None:
    await session.execute(delete(Chunk).where(Chunk.document_version_id == document_version_id))
    await session.execute(delete(Page).where(Page.document_version_id == document_version_id))
    await session.flush()


async def process_ingestion_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    storage_client: ObjectStorageClient,
    ocr_provider: OCRProvider | None = None,
    vector_writer: NoopVectorIndexWriter | None = None,
) -> None:
    """
    Core ingestion orchestration. Worker entrypoints and API reprocess share this logic.
    """
    settings = get_settings()
    ocr_provider = ocr_provider or StubOCRProvider()
    vector_writer = vector_writer or NoopVectorIndexWriter()

    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise AppError("INGESTION_JOB_NOT_FOUND", "Ingestion job not found", status_code=404)

    doc = await session.get(Document, job.document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)
    version = await session.get(DocumentVersion, job.document_version_id)
    if version is None:
        raise AppError("DOCUMENT_VERSION_NOT_FOUND", "Document version not found", status_code=404)

    file_format = _detect_format(doc)

    started = _now_utc()
    job.attempts += 1
    job.status = IngestionJobStatus.RUNNING
    job.stage = "parsing"
    job.progress = 0.05
    job.started_at = job.started_at or started
    job.error_code = None
    job.error_message = None
    job.metrics_json = job.metrics_json or {}

    logger.info(
        "ingestion.job.started",
        extra={
            "job_id": str(job.id),
            "document_id": str(doc.id),
            "document_version_id": str(version.id),
            "file_format": file_format,
        },
    )
    await session.flush()
    await session.commit()

    stage = "parsing"
    try:
        # Keep state transitions visible even when later stages fail.
        async with session.begin():
            stage = "parsing"
            job.stage = stage
            job.progress = 0.2
            job.metrics_json = {**(job.metrics_json or {}), "file_format": file_format}
            await session.flush()

            # Replace prior artifacts for this version.
            await _clear_version_artifacts(session, document_version_id=version.id)

            bucket = settings.s3_bucket_documents
            blob = await storage_client.get_object_bytes(bucket=bucket, key=version.storage_key)
            if not isinstance(blob, (bytes, bytearray)):
                raise AppError("STORAGE_READ_FAILED", "Failed to read object bytes", status_code=500)

            extracted_pages: list[ExtractedPage] = []
            ocr_pages = 0

            if file_format == "txt":
                raw = blob.decode("utf-8", errors="replace")
                page_number = 1
                native_text = raw.strip()

                if not native_text:
                    ocr_text, ocr_conf = await ocr_provider.ocr_empty_page()
                    ocr_pages = 1
                    extraction_method = PageExtractionMethod.OCR
                    raw = ocr_text
                    markdown = ocr_text
                    ocr_confidence = ocr_conf
                else:
                    extraction_method = PageExtractionMethod.NATIVE_TEXT
                    markdown = raw
                    ocr_confidence = None

                blocks: list[ExtractedBlock] = []
                order = 0
                for para in [p.strip() for p in raw.split("\n\n") if p.strip()]:
                    blocks.append(
                        ExtractedBlock(
                            block_type=StructuredBlockType.PARAGRAPH,
                            text=para,
                            order_index=order,
                        )
                    )
                    order += 1

                if not blocks:
                    blocks = [
                        ExtractedBlock(
                            block_type=StructuredBlockType.PARAGRAPH,
                            text=raw.strip(),
                            order_index=0,
                        )
                    ]

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        extraction_method=extraction_method,
                        raw_text=raw,
                        markdown_text=markdown,
                        blocks=blocks,
                        ocr_confidence=ocr_confidence,
                    )
                )

            elif file_format == "docx":
                import docx as docx_lib

                from io import BytesIO

                docx_file = docx_lib.Document(BytesIO(blob))
                raw_paras: list[tuple[str, str | None]] = []
                for p in docx_file.paragraphs:
                    text = (p.text or "").strip()
                    if not text:
                        continue
                    style_name = getattr(getattr(p, "style", None), "name", None)
                    raw_paras.append((text, style_name))

                page_number = 1
                native_text = "\n\n".join([t for t, _ in raw_paras]).strip()

                if not native_text:
                    ocr_text, ocr_conf = await ocr_provider.ocr_empty_page()
                    ocr_pages = 1
                    extraction_method = PageExtractionMethod.OCR
                    raw_combined = ocr_text
                    markdown = ocr_text
                    ocr_confidence = ocr_conf
                    raw_paras = [(ocr_text, None)]
                else:
                    extraction_method = PageExtractionMethod.NATIVE_TEXT
                    raw_combined = native_text
                    markdown = native_text
                    ocr_confidence = None

                blocks = []
                order = 0
                for text, style_name in raw_paras:
                    style_name = style_name or ""
                    if style_name.lower().startswith("heading"):
                        bt = StructuredBlockType.HEADING
                    else:
                        bt = StructuredBlockType.PARAGRAPH
                    blocks.append(
                        ExtractedBlock(
                            block_type=bt,
                            text=text,
                            order_index=order,
                            content_json={"style": style_name} if style_name else {},
                        )
                    )
                    order += 1

                if not blocks:
                    blocks = [
                        ExtractedBlock(
                            block_type=StructuredBlockType.PARAGRAPH,
                            text=raw_combined.strip(),
                            order_index=0,
                        )
                    ]

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        extraction_method=extraction_method,
                        raw_text=raw_combined,
                        markdown_text=markdown,
                        blocks=blocks,
                        ocr_confidence=ocr_confidence,
                    )
                )
            elif file_format == "pdf":
                # PDF ingestion uses PyMuPDF native text extraction per page.
                import fitz  # PyMuPDF

                pdf_doc = fitz.open(stream=blob, filetype="pdf")
                for page_idx in range(pdf_doc.page_count):
                    page = pdf_doc.load_page(page_idx)
                    text = page.get_text("text") or ""
                    text = text.strip()

                    page_number = page_idx + 1
                    if not text:
                        ocr_text, ocr_conf = await ocr_provider.ocr_empty_page()
                        ocr_pages += 1
                        extraction_method = PageExtractionMethod.OCR
                        raw_text = ocr_text
                        markdown_text = ocr_text
                        ocr_confidence = ocr_conf
                    else:
                        extraction_method = PageExtractionMethod.NATIVE_TEXT
                        raw_text = text
                        markdown_text = text
                        ocr_confidence = None

                    # Minimal structure: split by blank lines into paragraphs.
                    blocks: list[ExtractedBlock] = []
                    order = 0
                    for para in [p.strip() for p in raw_text.split("\n\n") if p.strip()]:
                        blocks.append(
                            ExtractedBlock(
                                block_type=StructuredBlockType.PARAGRAPH,
                                text=para,
                                order_index=order,
                            )
                        )
                        order += 1

                    if not blocks:
                        blocks = [
                            ExtractedBlock(
                                block_type=StructuredBlockType.PARAGRAPH,
                                text=raw_text.strip(),
                                order_index=0,
                            )
                        ]

                    extracted_pages.append(
                        ExtractedPage(
                            page_number=page_number,
                            extraction_method=extraction_method,
                            raw_text=raw_text,
                            markdown_text=markdown_text,
                            blocks=blocks,
                            ocr_confidence=ocr_confidence,
                        )
                    )
            else:
                raise AppError("UNSUPPORTED_MEDIA_TYPE", "Unsupported ingestion format", status_code=415)

            # Persist pages + structured blocks.
            page_rows: dict[int, Page] = {}
            for page in extracted_pages:
                page_row = Page(
                    document_version_id=version.id,
                    page_number=page.page_number,
                    extraction_method=page.extraction_method,
                    ocr_confidence=page.ocr_confidence,
                    raw_text=page.raw_text,
                    markdown_text=page.markdown_text,
                )
                session.add(page_row)
                await session.flush()
                page_rows[page.page_number] = page_row

                for blk in page.blocks:
                    # Store block text in content_json so chunk metadata and UI can use it later.
                    session.add(
                        StructuredBlock(
                            page_id=page_row.id,
                            block_type=blk.block_type,
                            level=blk.level,
                            order_index=blk.order_index,
                            content_json={**(blk.content_json or {}), "text": blk.text},
                        )
                    )

            await session.flush()

            # Diagnostics for job metrics.
            pages_processed = len(extracted_pages)
            blocks_processed = sum(len(p.blocks) for p in extracted_pages)
            logger.info(
                "ingestion.job.parsed",
                extra={
                    "job_id": str(job.id),
                    "pages_processed": pages_processed,
                    "blocks_processed": blocks_processed,
                    "ocr_pages": ocr_pages,
                },
            )

        # Chunking stage.
        stage = "chunking"
        async with session.begin():
            job.stage = stage
            job.progress = 0.6

            max_chars = getattr(settings, "chunk_max_chars", 2000)
            min_chars = getattr(settings, "chunk_min_chars", 200)
            overlap_chars = getattr(settings, "chunk_overlap_chars", 200)

            # Load pages+blocks for this version in order.
            pages = (await session.execute(select(Page).where(Page.document_version_id == version.id))).scalars().all()
            pages_by_number = {p.page_number: p for p in pages}
            # We chunk per page to keep page_id on chunks.

            # Ensure we stream blocks in reading order (order_index).
            chunks_created: list[Chunk] = []
            chunk_index = 0

            all_blocks = (
                await session.execute(
                    select(StructuredBlock)
                    .join(Page, Page.id == StructuredBlock.page_id)
                    .where(Page.document_version_id == version.id)
                    .order_by(StructuredBlock.page_id, StructuredBlock.order_index)
                )
            ).scalars().all()

            blocks_by_page: dict[UUID, list[StructuredBlock]] = {}
            for b in all_blocks:
                blocks_by_page.setdefault(b.page_id, []).append(b)

            for page in pages:
                p_blocks = blocks_by_page.get(page.id, [])

                # Derive chunk context from persisted structured blocks.
                section_heading = next(
                    (
                        (b.content_json.get("text") or "").strip()
                        for b in p_blocks
                        if b.block_type == StructuredBlockType.HEADING
                        and (b.content_json.get("text") or "").strip()
                    ),
                    None,
                )
                block_types = sorted({b.block_type.value for b in p_blocks})

                base_text = (page.markdown_text or "").strip()
                page_chunks = _chunk_text(
                    base_text,
                    max_chars=max_chars,
                    min_chars=min_chars,
                    overlap_chars=overlap_chars,
                )

                ocr_method = page.extraction_method.value
                for chunk_text in page_chunks:
                    # metadata: include page context and extraction method.
                    meta: dict[str, Any] = {
                        "workspace_id": str(doc.workspace_id),
                        "document_id": str(doc.id),
                        "document_version_id": str(version.id),
                        "page_number": page.page_number,
                        "section_heading": section_heading,
                        "extraction_method": ocr_method,
                        "block_types": block_types,
                    }
                    chunks_created.append(
                        Chunk(
                            document_version_id=version.id,
                            page_id=page.id,
                            chunk_index=chunk_index,
                            text=chunk_text,
                            token_count=_estimate_token_count(chunk_text),
                            embedding_model=settings.openai_embedding_model,
                            metadata_json=meta,
                            vector_id=None,
                        )
                    )
                    chunk_index += 1

            if chunks_created:
                session.add_all(chunks_created)
                await session.flush()
                for c in chunks_created:
                    c.vector_id = str(c.id)

            chunks_count = len(chunks_created)

            job.metrics_json = {
                **(job.metrics_json or {}),
                "chunks_created": chunks_count,
                "pages_processed": len(pages),
                "ocr_pages": ocr_pages,
            }
            logger.info(
                "ingestion.job.chunked",
                extra={"job_id": str(job.id), "chunks_created": chunks_count},
            )

        # Embedding/vector stage (contract stub).
        stage = "embedding"
        async with session.begin():
            job.stage = stage
            job.progress = 0.95

            chunks = (
                await session.execute(select(Chunk).where(Chunk.document_version_id == version.id))
            ).scalars().all()
            await vector_writer.index_chunks(chunks=chunks)

            logger.info(
                "ingestion.job.embedding_ready",
                extra={"job_id": str(job.id), "chunks_indexed": len(chunks)},
            )

        # Finalize.
        stage = "indexed"
        async with session.begin():
            job.stage = stage
            job.status = IngestionJobStatus.SUCCEEDED
            job.progress = 1.0
            job.finished_at = _now_utc()
            doc.status = DocumentLifecycleStatus.INDEXED
            job.error_code = None
            job.error_message = None
            await session.flush()

        logger.info(
            "ingestion.job.succeeded",
            extra={"job_id": str(job.id), "document_id": str(doc.id)},
        )

    except AppError as exc:
        # Domain failure (unsupported formats, storage, etc.)
        logger.error(
            "ingestion.job.failed_app_error",
            extra={"job_id": str(job.id), "stage": stage, "code": exc.code},
        )
        async with session.begin():
            job.status = IngestionJobStatus.FAILED
            job.stage = stage
            job.progress = float(job.progress or 0)
            job.finished_at = _now_utc()
            job.error_code = exc.code
            job.error_message = exc.message
            doc.status = DocumentLifecycleStatus.FAILED
            job.metrics_json = {**(job.metrics_json or {}), "failure": exc.message}
            await session.flush()
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingestion.job.failed", extra={"job_id": str(job.id), "stage": stage})
        async with session.begin():
            job.status = IngestionJobStatus.FAILED
            job.stage = stage
            job.progress = float(job.progress or 0)
            job.finished_at = _now_utc()
            job.error_code = "INGESTION_FAILED"
            job.error_message = str(exc)
            doc.status = DocumentLifecycleStatus.FAILED
            job.metrics_json = {**(job.metrics_json or {}), "failure": str(exc)}
            await session.flush()
        return
