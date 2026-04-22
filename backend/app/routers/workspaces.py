"""Workspace router (#46) — for the user-menu workspace switcher."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.cross import Workspace, WorkspaceMember
from app.models.user import User, UserRole
from app.services.plans import PLANS, usage_report
from app.services.workspaces import get_active_workspace_id

router = APIRouter(prefix="/api/me/workspaces", tags=["workspaces"], dependencies=[Depends(get_current_user)])


@router.get("/plans")
async def list_plan_tiers():
    """Static catalog of plan tiers + default caps. Used by the pricing page."""
    return {k: {"max_users": v.max_users, "max_projects": v.max_projects, "max_storage_mb": v.max_storage_mb}
            for k, v in PLANS.items()}


@router.get("/{workspace_id}/usage")
async def workspace_usage(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current usage vs plan caps for this workspace. Membership-checked for
    non-admins — admins can inspect any workspace."""
    if user.role != UserRole.ADMIN:
        is_member = (await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )).scalar_one_or_none()
        if not is_member:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return await usage_report(db, workspace_id)


@router.get("")
async def my_workspaces(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Workspaces visible to the current user. Admins see all. Annotates the
    one currently active so the UI can highlight it."""
    if user.role == UserRole.ADMIN:
        rows = (await db.execute(select(Workspace).order_by(Workspace.name))).scalars().all()
    else:
        rows = (
            await db.execute(
                select(Workspace)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == user.id)
                .order_by(Workspace.name)
            )
        ).scalars().all()
    active = await get_active_workspace_id(request, user, db)
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "slug": w.slug,
            "plan": w.plan,
            "active": w.id == active,
        }
        for w in rows
    ]
