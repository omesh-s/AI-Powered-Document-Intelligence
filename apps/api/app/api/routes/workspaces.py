from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DbSessionDep
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceListItem, WorkspaceResponse
from app.services import workspace_service

router = APIRouter()


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    body: WorkspaceCreateRequest,
) -> WorkspaceResponse:
    ws = await workspace_service.create_workspace(db, owner=current_user, name=body.name)
    return WorkspaceResponse.model_validate(ws)


@router.get("/", response_model=list[WorkspaceListItem])
async def list_workspaces(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[WorkspaceListItem]:
    rows = await workspace_service.list_workspaces_for_user(db, current_user.id)
    return [
        WorkspaceListItem(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            role=role.value,
            created_at=ws.created_at,
        )
        for ws, role in rows
    ]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> WorkspaceResponse:
    ws = await workspace_service.get_workspace_for_member(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    return WorkspaceResponse.model_validate(ws)
