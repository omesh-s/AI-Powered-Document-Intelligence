from __future__ import annotations

import re
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember


def _slug_base(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")[:72]
    return s or "workspace"


async def _slug_unique(session: AsyncSession, base: str) -> str:
    for _ in range(24):
        suffix = uuid.uuid4().hex[:10]
        candidate = f"{base}-{suffix}"
        if len(candidate) > 128:
            candidate = candidate[:128]
        exists = await session.scalar(select(Workspace.id).where(Workspace.slug == candidate))
        if exists is None:
            return candidate
    raise AppError("SLUG_GENERATION_FAILED", "Could not allocate workspace slug", status_code=500)


async def create_workspace(session: AsyncSession, *, owner: User, name: str) -> Workspace:
    base = _slug_base(name)
    slug = await _slug_unique(session, base)
    ws = Workspace(name=name.strip(), slug=slug)
    async with session.begin():
        session.add(ws)
        await session.flush()
        member = WorkspaceMember(
            workspace_id=ws.id,
            user_id=owner.id,
            role=WorkspaceRole.OWNER,
        )
        session.add(member)
        await session.flush()
    await session.refresh(ws)
    return ws


async def list_workspaces_for_user(
    session: AsyncSession, user_id: UUID
) -> list[tuple[Workspace, WorkspaceRole]]:
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at.desc())
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_workspace(session: AsyncSession, workspace_id: UUID) -> Workspace | None:
    return await session.get(Workspace, workspace_id)


async def require_workspace_member(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> WorkspaceMember:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    member = (await session.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise AppError(
            "WORKSPACE_ACCESS_DENIED",
            "You are not a member of this workspace",
            status_code=403,
        )
    return member


async def get_workspace_for_member(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> Workspace:
    ws = await get_workspace(session, workspace_id)
    if ws is None:
        raise AppError("WORKSPACE_NOT_FOUND", "Workspace not found", status_code=404)
    await require_workspace_member(session, workspace_id=workspace_id, user_id=user_id)
    return ws
