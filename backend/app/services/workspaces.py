"""Workspace isolation MVP (#46).

Phase-1 scope: a "Default" workspace is auto-seeded; existing rows on
flagship tables (projects, crm_companies, erp_vendors) get back-filled with
its id; new rows pick up the active workspace from the request.

Active-workspace resolution per request:
    1. `X-Workspace-Id` header — checked against WorkspaceMember
       (admins bypass the membership check).
    2. Otherwise the user's first workspace membership.
    3. Otherwise the Default workspace.

`get_active_workspace_id(request, user, db)` is the single entry point — call
it from any router that needs the active workspace.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Header, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.models.cross import Workspace, WorkspaceMember
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE_SLUG = "default"
DEFAULT_WORKSPACE_NAME = "Default workspace"


async def seed_default_workspace_and_backfill() -> None:
    """Idempotent boot-time helper: ensures a Default workspace exists, then
    backfills NULL workspace_id columns on flagship tables."""
    async with async_session() as db:
        # Get or create Default
        existing = (await db.execute(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))).scalar_one_or_none()
        if not existing:
            existing = Workspace(name=DEFAULT_WORKSPACE_NAME, slug=DEFAULT_WORKSPACE_SLUG, plan="default")
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
        default_id = existing.id

        # Backfill — best-effort. Each table guarded so a missing column doesn't tank startup.
        async with engine.begin() as conn:
            for table in ("projects", "crm_companies", "erp_vendors"):
                try:
                    await conn.execute(
                        text(f"UPDATE {table} SET workspace_id = :ws WHERE workspace_id IS NULL").bindparams(ws=default_id)
                    )
                except Exception:
                    logger.info("Workspace backfill: %s skipped", table, exc_info=True)


async def get_default_workspace(db: AsyncSession) -> Workspace | None:
    return (await db.execute(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))).scalar_one_or_none()


async def _user_has_membership(db: AsyncSession, user: User, workspace_id: UUID) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    r = await db.execute(
        select(WorkspaceMember.id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    return r.scalar_one_or_none() is not None


async def _user_first_workspace(db: AsyncSession, user: User) -> Workspace | None:
    r = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.created_at.asc())
        .limit(1)
    )
    return r.scalar_one_or_none()


async def get_active_workspace_id(
    request: Request,
    user: User,
    db: AsyncSession,
) -> UUID | None:
    """Resolve the active workspace for this request. Cached on request.state.
    Returns None only if there is no Default and the user belongs to nothing — in
    that case routers should treat the request as unscoped (legacy behaviour)."""
    cached = getattr(request.state, "_active_workspace_id", None)
    if cached is not None:
        return cached

    # 1. Honour the X-Workspace-Id header if the user has access
    header_val = request.headers.get("X-Workspace-Id")
    if header_val:
        try:
            wid = UUID(header_val)
            if await _user_has_membership(db, user, wid):
                request.state._active_workspace_id = wid
                return wid
        except Exception:
            pass

    # 2. First membership
    first = await _user_first_workspace(db, user)
    if first:
        request.state._active_workspace_id = first.id
        return first.id

    # 3. Default workspace
    default = await get_default_workspace(db)
    if default:
        request.state._active_workspace_id = default.id
        return default.id
    return None
