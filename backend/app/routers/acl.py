"""ACL admin and introspection endpoints.

* `GET /api/me/permissions` — the current user's effective codename set, used
  by the frontend to hide/disable UI that they can't act on.
* CRUD endpoints under `/api/admin/acl/*` for Groups, Permissions, user
  memberships, and direct user_permissions — consumed by the Admin app UI.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import _load_effective_codes, require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.acl import (
    Group,
    Permission,
    ProjectMember,
    UserPermission,
    group_permissions,
    user_groups,
)
from app.models.user import User, UserRole


router = APIRouter(prefix="/api", tags=["acl"])


# ── Schemas ──────────────────────────────────────────────────────────


class PermissionOut(BaseModel):
    id: uuid.UUID
    codename: str
    name: str
    description: str | None
    category: str


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupPermissionsUpdate(BaseModel):
    codenames: list[str]


class UserGroupsUpdate(BaseModel):
    group_ids: list[uuid.UUID]


class UserPermissionUpsert(BaseModel):
    codename: str
    is_deny: bool = False
    reason: str | None = None


class MePermissionsOut(BaseModel):
    role: str
    granted: list[str]
    denied: list[str]


class InspectResult(BaseModel):
    allowed: bool
    codename: str
    via: list[str]  # human-readable provenance lines


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool


class ProjectMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    role: str


class ProjectMemberUpsert(BaseModel):
    user_id: uuid.UUID
    role: str = "member"


# ── /api/me/permissions ──────────────────────────────────────────────


@router.get("/me/permissions", response_model=MePermissionsOut)
async def my_permissions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    granted, denied = await _load_effective_codes(db, user)
    return MePermissionsOut(role=user.role.value, granted=sorted(granted - denied), denied=sorted(denied))


# ── Permission catalog (read-only) ───────────────────────────────────


@router.get("/admin/acl/permissions", response_model=list[PermissionOut])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    rows = (await db.scalars(select(Permission).order_by(Permission.category, Permission.codename))).all()
    return [PermissionOut(id=p.id, codename=p.codename, name=p.name, description=p.description, category=p.category) for p in rows]


# ── Groups ───────────────────────────────────────────────────────────


@router.get("/admin/acl/groups", response_model=list[GroupOut])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    rows = (await db.scalars(select(Group).order_by(Group.name))).all()
    return [GroupOut(id=g.id, name=g.name, description=g.description, is_system=g.is_system) for g in rows]


@router.post("/admin/acl/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    exists = await db.scalar(select(Group.id).where(Group.name == body.name))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Group name already exists")
    g = Group(name=body.name, description=body.description, is_system=False)
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return GroupOut(id=g.id, name=g.name, description=g.description, is_system=g.is_system)


@router.delete("/admin/acl/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    g = await db.get(Group, group_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    if g.is_system:
        raise HTTPException(status.HTTP_409_CONFLICT, "System groups cannot be deleted")
    await db.delete(g)
    await db.commit()


@router.get("/admin/acl/groups/{group_id}/permissions", response_model=list[str])
async def get_group_permissions(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    q = (
        select(Permission.codename)
        .join(group_permissions, group_permissions.c.permission_id == Permission.id)
        .where(group_permissions.c.group_id == group_id)
    )
    return sorted((await db.scalars(q)).all())


@router.put("/admin/acl/groups/{group_id}/permissions", response_model=list[str])
async def set_group_permissions(
    group_id: uuid.UUID,
    body: GroupPermissionsUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    g = await db.get(Group, group_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    perms = {
        p.codename: p
        for p in (await db.scalars(select(Permission).where(Permission.codename.in_(body.codenames)))).all()
    }
    missing = [c for c in body.codenames if c not in perms]
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown codenames: {missing}")

    await db.execute(delete(group_permissions).where(group_permissions.c.group_id == group_id))
    for p in perms.values():
        await db.execute(group_permissions.insert().values(group_id=group_id, permission_id=p.id))
    await db.commit()
    return sorted(perms.keys())


# ── User ↔ Group membership ──────────────────────────────────────────


@router.get("/admin/acl/users/{user_id}/groups", response_model=list[GroupOut])
async def get_user_groups(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    q = (
        select(Group)
        .join(user_groups, user_groups.c.group_id == Group.id)
        .where(user_groups.c.user_id == user_id)
    )
    rows = (await db.scalars(q)).all()
    return [GroupOut(id=g.id, name=g.name, description=g.description, is_system=g.is_system) for g in rows]


@router.put("/admin/acl/users/{user_id}/groups", response_model=list[GroupOut])
async def set_user_groups(
    user_id: uuid.UUID,
    body: UserGroupsUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    groups = (await db.scalars(select(Group).where(Group.id.in_(body.group_ids)))).all() if body.group_ids else []
    if len(groups) != len(set(body.group_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown group ids")

    await db.execute(delete(user_groups).where(user_groups.c.user_id == user_id))
    for g in groups:
        await db.execute(user_groups.insert().values(user_id=user_id, group_id=g.id))
    await db.commit()
    return [GroupOut(id=g.id, name=g.name, description=g.description, is_system=g.is_system) for g in groups]


# ── Direct user permissions (allow + deny overrides) ────────────────


@router.get("/admin/acl/users/{user_id}/permissions")
async def get_user_direct_permissions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    q = (
        select(Permission.codename, UserPermission.is_deny, UserPermission.reason)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user_id)
    )
    return [
        {"codename": code, "is_deny": is_deny, "reason": reason}
        for code, is_deny, reason in (await db.execute(q)).all()
    ]


@router.post("/admin/acl/users/{user_id}/permissions")
async def upsert_user_permission(
    user_id: uuid.UUID,
    body: UserPermissionUpsert,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    p = await db.scalar(select(Permission).where(Permission.codename == body.codename))
    if p is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown codename: {body.codename}")
    existing = await db.scalar(
        select(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == p.id,
        )
    )
    if existing is None:
        db.add(UserPermission(user_id=user_id, permission_id=p.id, is_deny=body.is_deny, reason=body.reason))
    else:
        existing.is_deny = body.is_deny
        existing.reason = body.reason
    await db.commit()
    return {"ok": True}


@router.delete("/admin/acl/users/{user_id}/permissions/{codename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_permission(
    user_id: uuid.UUID,
    codename: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    p = await db.scalar(select(Permission).where(Permission.codename == codename))
    if p is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown codename: {codename}")
    await db.execute(
        delete(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == p.id,
        )
    )
    await db.commit()


# ── Permission inspector ─────────────────────────────────────────────


@router.get("/admin/acl/inspect", response_model=InspectResult)
async def inspect_permission(
    user_id: uuid.UUID,
    codename: str,
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.permission.assign")),
):
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    perm = await db.scalar(select(Permission).where(Permission.codename == codename))
    if perm is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown codename: {codename}")

    via: list[str] = []

    # Role
    if target.role == UserRole.ADMIN:
        via.append("granted by role=admin (blanket)")

    # Groups that grant it
    group_q = (
        select(Group.name)
        .join(group_permissions, group_permissions.c.group_id == Group.id)
        .join(user_groups, user_groups.c.group_id == Group.id)
        .where(user_groups.c.user_id == user_id, group_permissions.c.permission_id == perm.id)
    )
    for gname in (await db.scalars(group_q)).all():
        via.append(f"granted via group '{gname}'")

    # Direct grant or deny
    up = await db.scalar(
        select(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == perm.id,
        )
    )
    if up is not None:
        if up.is_deny:
            via.append(f"DENIED directly (reason: {up.reason or '—'})")
        else:
            via.append(f"granted directly (reason: {up.reason or '—'})")

    # Project membership (when applicable)
    if project_id is not None and codename.startswith("projects.") and target.role != UserRole.ADMIN:
        member = await db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        if member is None:
            via.append(f"BLOCKED: not a member of project {project_id}")

    # Final answer — reuse the same path as runtime
    from app.acl.resolver import has_permission
    allowed = await has_permission(db, target, codename, project_id=project_id)

    return InspectResult(allowed=allowed, codename=codename, via=via or ["no matching grant"])


# ── Users (admin-facing directory for the UI) ────────────────────────


@router.get("/admin/users", response_model=list[UserSummary])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.user.manage")),
):
    rows = (await db.scalars(select(User).order_by(User.email))).all()
    return [
        UserSummary(id=u.id, email=u.email, name=u.name, role=u.role.value, is_active=u.is_active)
        for u in rows
    ]


# ── Project membership ───────────────────────────────────────────────


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
async def list_project_members(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Anyone signed in can see the member list of a project they can view.
    Write access is gated by admin.group.manage."""
    q = (
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.email)
    )
    rows = (await db.execute(q)).all()
    return [
        ProjectMemberOut(id=m.id, user_id=u.id, user_email=u.email, user_name=u.name, role=m.role)
        for m, u in rows
    ]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: uuid.UUID,
    body: ProjectMemberUpsert,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    existing = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == body.user_id,
        )
    )
    if existing is not None:
        existing.role = body.role
        m = existing
    else:
        m = ProjectMember(project_id=project_id, user_id=body.user_id, role=body.role)
        db.add(m)
    await db.commit()
    await db.refresh(m)
    return ProjectMemberOut(id=m.id, user_id=user.id, user_email=user.email, user_name=user.name, role=m.role)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("admin.group.manage")),
):
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    await db.commit()
