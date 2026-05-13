from __future__ import annotations

import asyncio
import sys
from uuid import UUID

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.storage import S3ObjectStorage
from app.services.ingestion_service import process_ingestion_job


async def run_job(job_id: UUID) -> None:
    settings = get_settings()
    storage = S3ObjectStorage.from_settings()
    async with AsyncSessionLocal() as session:
        await process_ingestion_job(session, job_id=job_id, storage_client=storage)


def run_job_sync(job_id: UUID) -> None:
    asyncio.run(run_job(job_id))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.workers.ingestion_runner <ingestion_job_id>")
    job_id_str = sys.argv[1]
    job_id = UUID(job_id_str)
    run_job_sync(job_id)


if __name__ == "__main__":
    main()

