from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/jobs")
async def admin_jobs() -> None:
    raise HTTPException(status_code=501, detail="Implemented in a later phase")


@router.get("/documents/{document_id}/diagnostics")
async def document_diagnostics(document_id: str) -> None:
    _ = document_id
    raise HTTPException(status_code=501, detail="Implemented in a later phase")
