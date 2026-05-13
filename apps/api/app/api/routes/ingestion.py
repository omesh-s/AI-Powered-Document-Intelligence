from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserDep, DbSessionDep
from app.core.errors import AppError
from app.models.document import Document
from app.models.ingestion import IngestionJob
from app.models.enums import IngestionJobStatus
from app.models.workspace import WorkspaceMember
from app.schemas.ingestion import (
    DocumentIngestionSummary,
    IngestionJobDetailResponse,
    IngestionJobListResponse,
    IngestionJobSummary,
)
from app.schemas.pagination import PaginatedMeta
from app.services.workspace_service import require_workspace_member
from app.core.logging import get_logger

router = APIRouter()

logger = get_logger(__name__)


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


@router.get("/jobs", response_model=IngestionJobListResponse)
async def list_jobs(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    workspace_id: UUID | None = Query(
        None, description="Filter by workspace id (member visibility enforced)"
    ),
    document_id: UUID | None = Query(
        None, description="Filter by document id (member visibility enforced)"
    ),
    status: IngestionJobStatus | None = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> IngestionJobListResponse:
    # List with membership enforced by joining through workspace_members.
    base_filters = [
        Document.deleted_at.is_(None),
        WorkspaceMember.user_id == current_user.id,
    ]
    if workspace_id is not None:
        base_filters.append(Document.workspace_id == workspace_id)
    if document_id is not None:
        base_filters.append(IngestionJob.document_id == document_id)
    if status is not None:
        base_filters.append(IngestionJob.status == status)

    join_stmt = (
        select(IngestionJob, Document)
        .join(Document, Document.id == IngestionJob.document_id)
        .join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Document.workspace_id,
        )
        .where(*base_filters)
    )

    count_stmt = (
        select(func.count(IngestionJob.id))
        .select_from(IngestionJob)
        .join(Document, Document.id == IngestionJob.document_id)
        .join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Document.workspace_id,
        )
        .where(*base_filters)
    )

    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        join_stmt.order_by(IngestionJob.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).all()

    items: list[IngestionJobSummary] = []
    for job, _doc in rows:
        items.append(_job_to_summary(job))

    return IngestionJobListResponse(
        items=items,
        pagination=PaginatedMeta(page=page, size=size, total=total),
    )

@router.get("/jobs/{job_id}", response_model=IngestionJobDetailResponse)
async def get_job(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    job_id: UUID,
) -> IngestionJobDetailResponse:
    job = await db.get(IngestionJob, job_id)
    if job is None:
        raise AppError("INGESTION_JOB_NOT_FOUND", "Ingestion job not found", status_code=404)

    doc = await db.get(Document, job.document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found", status_code=404)

    await require_workspace_member(
        db,
        workspace_id=doc.workspace_id,
        user_id=current_user.id,
    )

    return IngestionJobDetailResponse(
        job=_job_to_summary(job),
        document=_doc_to_summary(doc),
        metrics=job.metrics_json,
    )
