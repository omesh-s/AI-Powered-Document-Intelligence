from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedMeta


class DocumentIngestionSummary(BaseModel):
    id: UUID
    filename: str
    content_type: str
    status: str
    workspace_id: UUID

    created_at: datetime


class IngestionJobSummary(BaseModel):
    id: UUID
    document_id: UUID
    document_version_id: UUID
    status: str
    stage: str
    progress: float

    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None

    error_code: str | None = None
    error_message: str | None = None


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobSummary]
    pagination: PaginatedMeta


class IngestionJobDetailResponse(BaseModel):
    job: IngestionJobSummary
    document: DocumentIngestionSummary
    metrics: dict[str, Any] | None = None


class IngestionReprocessResponse(BaseModel):
    job: IngestionJobSummary
    document: DocumentIngestionSummary | None = None
    request_id: str = Field(..., description="X-Request-ID from the API request")

