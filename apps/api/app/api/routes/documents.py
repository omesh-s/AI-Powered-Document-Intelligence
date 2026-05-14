from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUserDep, DbSessionDep, StorageDep
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models.enums import DocumentLifecycleStatus
from app.schemas.document import (
    DocumentChunksResponse,
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentPagesResponse,
    DocumentResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.ingestion import IngestionReprocessResponse
from app.services import document_service
from app.services import ingestion_service

router = APIRouter()

_settings = get_settings()
_UPLOAD_URL = f"{_settings.rate_limit_upload_url_per_minute}/minute"
_DOC_CREATE = f"{_settings.rate_limit_document_create_per_minute}/minute"


@router.post("/upload-url", response_model=UploadUrlResponse)
@limiter.limit(_UPLOAD_URL)
async def request_upload_url(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
    body: UploadUrlRequest,
) -> UploadUrlResponse:
    _ = request
    return await document_service.request_presigned_upload(
        db,
        storage,
        actor=current_user,
        workspace_id=body.workspace_id,
        filename=body.filename,
        content_type=body.content_type,
        file_size=body.file_size,
    )


@router.post("/", response_model=DocumentResponse)
@limiter.limit(_DOC_CREATE)
async def create_document(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    body: DocumentCreateRequest,
) -> DocumentResponse:
    _ = request
    return await document_service.create_document_after_upload(
        db,
        actor=current_user,
        workspace_id=body.workspace_id,
        filename=body.filename,
        content_type=body.content_type,
        file_size=body.file_size,
        storage_key=body.storage_key,
        checksum_sha256=body.checksum_sha256,
        metadata=body.metadata,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    workspace_id: UUID = Query(..., description="Workspace to list documents for"),
    status: DocumentLifecycleStatus | None = Query(None, description="Filter by document lifecycle status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> DocumentListResponse:
    return await document_service.list_documents(
        db,
        actor=current_user,
        workspace_id=workspace_id,
        page=page,
        size=size,
        status=status,
    )


@router.get("/{document_id}/pages", response_model=DocumentPagesResponse)
async def list_document_pages(
    document_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> DocumentPagesResponse:
    return await document_service.list_document_pages(
        db,
        actor=current_user,
        document_id=document_id,
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def list_document_chunks(
    document_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> DocumentChunksResponse:
    return await document_service.list_document_chunks(
        db,
        actor=current_user,
        document_id=document_id,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> DocumentResponse:
    return await document_service.get_document(
        db,
        actor=current_user,
        document_id=document_id,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    await document_service.soft_delete_document(
        db,
        actor=current_user,
        document_id=document_id,
    )


@router.post("/{document_id}/reprocess", response_model=IngestionReprocessResponse)
async def reprocess_document(
    request: Request,
    document_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> IngestionReprocessResponse:
    request_id = getattr(request.state, "request_id", "")
    job, doc = await ingestion_service.create_reprocess_job(
        db,
        actor=current_user,
        document_id=document_id,
    )
    return IngestionReprocessResponse(
        job=job,
        document=doc,
        request_id=request_id,
    )
