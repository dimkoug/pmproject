"""Permission resolver and FastAPI dependency.

Resolution rules:

    1. If user.role == ADMIN, every permission is granted (unless explicitly
       denied via a UserPermission.is_deny row — admin denies are rare but
       preserved because the data model supports them).
    2. Otherwise collect the set of codenames the user has via:
         * groups they belong to
         * direct UserPermission rows with is_deny=False
    3. Subtract codenames from direct UserPermission rows with is_deny=True.
    4. If the check carries a project_id, also require ProjectMember(project_id,
       user_id) — unless the user is ADMIN or the required codename starts with
       a non-project prefix (sales/finance/documents/admin).

Cached per-request via a dict stashed on the Request state.
"""

from __future__ import annotations

from uuid import UUID
from typing import Iterable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.acl import Group, Permission, ProjectMember, UserPermission, group_permissions, user_groups
from app.models.user import User, UserRole


# ── Core resolution ───────────────────────────────────────────────────────


async def _load_effective_codes(db: AsyncSession, user: User) -> tuple[set[str], set[str]]:
    """Return (granted_codes, denied_codes) for a user.

    The caller subtracts denied from granted. We keep them separate so
    `/api/me/permissions` can surface explicit denials in the inspector UI.
    """
    if user.role == UserRole.ADMIN:
        # Admin gets all codenames; explicit denies still apply
        all_codes = set(
            (await db.scalars(select(Permission.codename))).all()
        )
    else:
        # Group-granted permissions
        group_q = (
            select(Permission.codename)
            .join(group_permissions, group_permissions.c.permission_id == Permission.id)
            .join(Group, Group.id == group_permissions.c.group_id)
            .join(user_groups, user_groups.c.group_id == Group.id)
            .where(user_groups.c.user_id == user.id)
        )
        all_codes = set((await db.scalars(group_q)).all())

    # Direct user permissions — allow or deny
    direct_q = (
        select(Permission.codename, UserPermission.is_deny)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user.id)
    )
    denied: set[str] = set()
    for code, is_deny in (await db.execute(direct_q)).all():
        if is_deny:
            denied.add(code)
        else:
            all_codes.add(code)

    return all_codes, denied


async def _user_effective(db: AsyncSession, user: User, request: Request | None = None) -> set[str]:
    """Granted minus denied. Memoised on request state if available."""
    if request is not None:
        cache = getattr(request.state, "_acl_cache", None)
        if cache is None:
            cache = {}
            request.state._acl_cache = cache
        if user.id in cache:
            return cache[user.id]

    granted, denied = await _load_effective_codes(db, user)
    effective = granted - denied

    if request is not None:
        request.state._acl_cache[user.id] = effective
    return effective


async def has_permission(
    db: AsyncSession,
    user: User,
    codename: str,
    *,
    project_id: UUID | None = None,
    request: Request | None = None,
) -> bool:
    """Single entry point callers can use outside the FastAPI dependency system.

    When `project_id` is supplied and the codename belongs to the `projects.*`
    category, require ProjectMember membership in addition to the global grant.
    """
    effective = await _user_effective(db, user, request=request)
    if codename not in effective:
        return False

    if project_id is not None and codename.startswith("projects.") and user.role != UserRole.ADMIN:
        member = await db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
        if member is None:
            return False

    return True


# ── FastAPI dependency factory ────────────────────────────────────────────


def require_permission(codename: str, *, allow_any: Iterable[str] | None = None):
    """Build a FastAPI dependency that enforces a codename.

    Usage:
        @router.post("/invoices")
        async def create(..., _: None = Depends(require_permission("finance.invoice.create"))):
            ...

    Pass `allow_any=("code.a", "code.b")` to accept *either* of a group of
    codes (useful for endpoints that serve both read and write roles).
    """
    codes = (codename, *(allow_any or ()))

    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        effective = await _user_effective(db, user, request=request)
        if not any(c in effective for c in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {codename}",
            )
        return None

    return _dep


async def require_project_permission_body(
    codename: str,
    project_id: UUID,
    user: User,
    db: AsyncSession,
    request: Request | None = None,
) -> None:
    """Callable form for project-scoped checks — use inside handlers when the
    project_id is only available after parsing the body."""
    if not await has_permission(db, user, codename, project_id=project_id, request=request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {codename} (project {project_id})",
        )
