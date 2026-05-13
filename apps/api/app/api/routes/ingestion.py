from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/jobs")
async def list_jobs() -> None:
    raise HTTPException(status_code=501, detail="Implemented in a later phase")


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> None:
    _ = job_id
    raise HTTPException(status_code=501, detail="Implemented in a later phase")
