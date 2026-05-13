from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedMeta


class UploadUrlRequest(BaseModel):
    workspace_id: UUID
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=3, max_length=255)
    file_size: int = Field(..., ge=1)


class UploadUrlResponse(BaseModel):
    storage_key: str
    upload_url: str
    expires_in_seconds: int
    required_headers: dict[str, str]


class DocumentCreateRequest(BaseModel):
    workspace_id: UUID
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=3, max_length=255)
    file_size: int = Field(..., ge=1)
    storage_key: str = Field(..., min_length=8, max_length=1024)
    checksum_sha256: str | None = Field(None, max_length=64)
    metadata: dict[str, Any] | None = None


class IngestionJobSummary(BaseModel):
    id: UUID
    status: str
    stage: str
    progress: float


class DocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    content_type: str
    file_size: int
    storage_key: str
    status: str
    latest_version_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    ingestion_job: IngestionJobSummary | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    pagination: PaginatedMeta
