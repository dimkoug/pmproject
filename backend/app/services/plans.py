"""Workspace plan limits (#8).

Three pricing tiers with hard caps on users/projects/storage. Checked at
key entry points (signup, invite, project create, file upload). A
workspace row can override any individual limit via its
`max_users` / `max_projects` / `max_storage_mb` columns — set NULL to
inherit the plan default.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PlanLimits:
    max_users: int
    max_projects: int
    max_storage_mb: int


# Chosen to match typical SaaS tiers; adjust in one place when product changes.
PLANS: dict[str, PlanLimits] = {
    "free":       PlanLimits(max_users=3,   max_projects=2,   max_storage_mb=500),
    "pro":        PlanLimits(max_users=25,  max_projects=50,  max_storage_mb=20_000),
    "enterprise": PlanLimits(max_users=10_000, max_projects=10_000, max_storage_mb=1_000_000),
}


def _limits_for(plan: str) -> PlanLimits:
    return PLANS.get(plan, PLANS["free"])


async def get_effective_limits(db: AsyncSession, workspace_id) -> PlanLimits:
    """Resolve the effective limits for a workspace — per-row overrides
    win over plan defaults, otherwise fall back to the plan tier."""
    from app.models.cross import Workspace
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        return PLANS["free"]
    d = _limits_for(ws.plan)
    return PlanLimits(
        max_users=ws.max_users if ws.max_users is not None else d.max_users,
        max_projects=ws.max_projects if ws.max_projects is not None else d.max_projects,
        max_storage_mb=ws.max_storage_mb if ws.max_storage_mb is not None else d.max_storage_mb,
    )


async def _count_members(db: AsyncSession, workspace_id) -> int:
    from app.models.cross import WorkspaceMember
    row = (await db.execute(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace_id)
    )).scalar_one()
    return int(row or 0)


async def _count_projects(db: AsyncSession, workspace_id) -> int:
    from app.models.project import Project
    row = (await db.execute(
        select(func.count(Project.id))
        .where(Project.workspace_id == workspace_id, Project.deleted_at.is_(None))
    )).scalar_one()
    return int(row or 0)


async def _sum_storage_mb(db: AsyncSession, workspace_id) -> int:
    """Sum document-version sizes across all folders in this workspace."""
    try:
        from app.models.dms import Document, DocumentVersion, Folder
        bytes_sum = (await db.execute(
            select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0))
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Folder, Document.folder_id == Folder.id)
            .where(Folder.workspace_id == workspace_id)
        )).scalar_one()
        return int(int(bytes_sum or 0) / (1024 * 1024))
    except Exception:
        return 0


async def check_can_add_member(db: AsyncSession, workspace_id) -> None:
    limits = await get_effective_limits(db, workspace_id)
    if await _count_members(db, workspace_id) >= limits.max_users:
        raise HTTPException(status_code=402, detail={
            "error": "plan_limit_reached", "limit": "users", "cap": limits.max_users,
            "hint": "Upgrade your plan to invite more members.",
        })


async def check_can_add_project(db: AsyncSession, workspace_id) -> None:
    limits = await get_effective_limits(db, workspace_id)
    if await _count_projects(db, workspace_id) >= limits.max_projects:
        raise HTTPException(status_code=402, detail={
            "error": "plan_limit_reached", "limit": "projects", "cap": limits.max_projects,
            "hint": "Upgrade your plan to create more projects.",
        })


async def check_can_upload(db: AsyncSession, workspace_id, new_bytes: int) -> None:
    limits = await get_effective_limits(db, workspace_id)
    current_mb = await _sum_storage_mb(db, workspace_id)
    incoming_mb = max(1, int(new_bytes / (1024 * 1024)))
    if current_mb + incoming_mb > limits.max_storage_mb:
        raise HTTPException(status_code=402, detail={
            "error": "plan_limit_reached", "limit": "storage_mb",
            "cap": limits.max_storage_mb, "used_mb": current_mb,
            "hint": "Upgrade your plan or delete old files.",
        })


async def usage_report(db: AsyncSession, workspace_id) -> dict:
    """Snapshot of current usage vs plan limits — served by GET /api/workspaces/{id}/usage."""
    limits = await get_effective_limits(db, workspace_id)
    users = await _count_members(db, workspace_id)
    projects = await _count_projects(db, workspace_id)
    storage_mb = await _sum_storage_mb(db, workspace_id)
    return {
        "limits": {"max_users": limits.max_users, "max_projects": limits.max_projects, "max_storage_mb": limits.max_storage_mb},
        "usage": {"users": users, "projects": projects, "storage_mb": storage_mb},
        "remaining": {
            "users": max(0, limits.max_users - users),
            "projects": max(0, limits.max_projects - projects),
            "storage_mb": max(0, limits.max_storage_mb - storage_mb),
        },
    }
