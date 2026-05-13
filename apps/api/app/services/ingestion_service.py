from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IngestionJobStatus
from app.models.ingestion import IngestionJob


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
