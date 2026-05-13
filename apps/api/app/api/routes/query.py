from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/ask")
async def ask() -> None:
    raise HTTPException(status_code=501, detail="Implemented in a later phase")


@router.get("/sessions")
async def list_sessions() -> None:
    raise HTTPException(status_code=501, detail="Implemented in a later phase")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> None:
    _ = session_id
    raise HTTPException(status_code=501, detail="Implemented in a later phase")
