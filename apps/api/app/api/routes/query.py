from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUserDep, DbSessionDep
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.query import (
    AskRequest,
    AskResponse,
    QuerySessionDetailResponse,
    QuerySessionListResponse,
)
from app.services import query_service

router = APIRouter()
_settings = get_settings()
_QUERY_LIMIT = f"{_settings.rate_limit_query_per_minute}/minute"


@router.post("/ask", response_model=AskResponse)
@limiter.limit(_QUERY_LIMIT)
async def ask(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    body: AskRequest,
) -> AskResponse:
    _ = request
    return await query_service.ask(db, actor=current_user, body=body)


@router.get("/sessions", response_model=QuerySessionListResponse)
@limiter.limit(_QUERY_LIMIT)
async def list_sessions(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    workspace_id: Annotated[UUID, Query(description="Workspace to list sessions for")],
    document_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> QuerySessionListResponse:
    _ = request
    return await query_service.list_sessions(
        db,
        actor=current_user,
        workspace_id=workspace_id,
        document_id=document_id,
        page=page,
        size=size,
    )


@router.get("/sessions/{session_id}", response_model=QuerySessionDetailResponse)
@limiter.limit(_QUERY_LIMIT)
async def get_session(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    session_id: UUID,
) -> QuerySessionDetailResponse:
    _ = request
    return await query_service.get_session_detail(db, actor=current_user, session_id=session_id)
