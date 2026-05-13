from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import (
    ObjectStorageClient,
    build_presigned_upload_object_key,
    storage_key_is_within_workspace_scope,
)
from app.models.document import Document, DocumentVersion
from app.models.enums import DocumentLifecycleStatus
from app.models.ingestion import IngestionJob
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    IngestionJobSummary,
    UploadUrlResponse,
)
from app.schemas.pagination import PaginatedMeta
from app.services import audit_service, ingestion_service
from app.services.workspace_service import require_workspace_member


def _validate_upload_constraints(*, content_type: str, file_size: int) -> None:
    settings = get_settings()
    allowed = settings.allowed_upload_mime_set()
    if content_type.strip().lower() not in allowed:
        raise AppError(
            "UNSUPPORTED_MEDIA_TYPE",
            "This file type is not allowed",
            status_code=415,
            details={"content_type": content_type},
        )
    if file_size > settings.max_upload_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            "File exceeds maximum allowed size",
            status_code=413,
            details={"max_bytes": settings.max_upload_bytes},
        )


async def request_presigned_upload(
    session: AsyncSession,
    storage: ObjectStorageClient,
    *,
    actor: User,
    workspace_id: UUID,
    filename: str,
    content_type: str,
    file_size: int,
) -> UploadUrlResponse:
    _validate_upload_constraints(content_type=content_type, file_size=file_size)
    await require_workspace_member(session, workspace_id=workspace_id, user_id=actor.id)
    try:
        object_key = build_presigned_upload_object_key(
            workspace_id=workspace_id,
            user_id=actor.id,
            original_filename=filename,
        )
    except ValueError as exc:
        raise AppError("INVALID_FILENAME", str(exc), status_code=400) from exc

    settings = get_settings()
    presigned = storage.presign_put_object(
        bucket=settings.s3_bucket_documents,
        key=object_key,
        content_type=content_type.strip(),
        expires_in=settings.s3_presign_expires_seconds,
    )
    return UploadUrlResponse(
        storage_key=presigned.object_key,
        upload_url=presigned.url,
        expires_in_seconds=settings.s3_presign_expires_seconds,
        required_headers=presigned.headers,
    )


def _job_to_summary(job: IngestionJob | None) -> IngestionJobSummary | None:
    if job is None:
        return None
    return IngestionJobSummary(
        id=job.id,
        status=job.status.value,
        stage=job.stage,
        progress=float(job.progress),
    )


def _document_to_response(
    doc: Document,
    *,
    ingestion_job: IngestionJob | None = None,
) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        workspace_id=doc.workspace_id,
        filename=doc.filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        storage_key=doc.storage_key,
        status=doc.status.value,
        latest_version_id=doc.latest_version_id,
        created_by=doc.created_by,
        created_at=doc.created_at,
        ingestion_job=_job_to_summary(ingestion_job),
    )


async def _latest_ingestion_job(session: AsyncSession, document_id: UUID) -> IngestionJob | None:
    stmt = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_document_after_upload(
    session: AsyncSession,
    *,
    actor: User,
    workspace_id: UUID,
    filename: str,
    content_type: str,
    file_size: int,
    storage_key: str,
    checksum_sha256: str | None,
    metadata: dict[str, Any] | None,
) -> DocumentResponse:
    _validate_upload_constraints(content_type=content_type, file_size=file_size)
    await require_workspace_member(session, workspace_id=workspace_id, user_id=actor.id)
    if not storage_key_is_within_workspace_scope(
        storage_key,
        workspace_id=workspace_id,
        user_id=actor.id,
    ):
        raise AppError(
            "INVALID_STORAGE_KEY",
            "Storage key is not valid for this workspace or user",
            status_code=400,
        )

    meta: dict[str, Any] = dict(metadata) if metadata else {}
    if checksum_sha256:
        meta["checksum_sha256"] = checksum_sha256

    document = Document(
        workspace_id=workspace_id,
        filename=filename.strip(),
        content_type=content_type.strip(),
        file_size=file_size,
        storage_key=storage_key,
        status=DocumentLifecycleStatus.QUEUED,
        created_by=actor.id,
    )
    job: IngestionJob
    async with session.begin():
        session.add(document)
        await session.flush()

        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            storage_key=storage_key,
            file_sha256=checksum_sha256,
            metadata_json=meta or None,
        )
        session.add(version)
        await session.flush()

        document.latest_version_id = version.id
        await session.flush()

        job = await ingestion_service.create_queued_ingestion_job(
            session,
            document_id=document.id,
            document_version_id=version.id,
        )

        await audit_service.record_audit(
            session,
            workspace_id=workspace_id,
            user_id=actor.id,
            action="document.created",
            resource_type="document",
            resource_id=document.id,
            metadata={"filename": document.filename, "ingestion_job_id": str(job.id)},
        )

    await session.refresh(document)
    await session.refresh(job)
    return _document_to_response(document, ingestion_job=job)


async def list_documents(
    session: AsyncSession,
    *,
    actor: User,
    workspace_id: UUID,
    page: int,
    size: int,
) -> DocumentListResponse:
    await require_workspace_member(session, workspace_id=workspace_id, user_id=actor.id)
    base_filter = (
        Document.workspace_id == workspace_id,
        Document.deleted_at.is_(None),
    )
    count_stmt = select(func.count()).select_from(Document).where(*base_filter)
    total = int((await session.execute(count_stmt)).scalar_one())
    stmt = (
        select(Document)
        .where(*base_filter)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await session.execute(stmt)).scalars().all()
    items: list[DocumentResponse] = []
    for doc in rows:
        job = await _latest_ingestion_job(session, doc.id)
        items.append(_document_to_response(doc, ingestion_job=job))
    return DocumentListResponse(
        items=items,
        pagination=PaginatedMeta(page=page, size=size, total=total),
    )


async def get_document(
    session: AsyncSession,
    *,
    actor: User,
    document_id: UUID,
) -> DocumentResponse:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)
    await require_workspace_member(session, workspace_id=doc.workspace_id, user_id=actor.id)
    job = await _latest_ingestion_job(session, doc.id)
    return _document_to_response(doc, ingestion_job=job)


async def soft_delete_document(
    session: AsyncSession,
    *,
    actor: User,
    document_id: UUID,
) -> None:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)
    await require_workspace_member(session, workspace_id=doc.workspace_id, user_id=actor.id)
    async with session.begin():
        doc.deleted_at = datetime.now(tz=timezone.utc)
        await audit_service.record_audit(
            session,
            workspace_id=doc.workspace_id,
            user_id=actor.id,
            action="document.deleted",
            resource_type="document",
            resource_id=doc.id,
            metadata=None,
        )
