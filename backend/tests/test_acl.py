"""Tests for the ACL system: resolver logic, endpoints, and project membership.

The conftest seeds the full Permission catalog and uses an ADMIN test user, so
admin endpoints succeed by default. Tests that exercise non-admin behaviour
override `get_current_user` locally.
"""

import uuid
import pytest
from httpx import AsyncClient

from app.acl.resolver import _load_effective_codes, has_permission
from app.dependencies import get_current_user
from app.main import app
from app.models.acl import Group, UserPermission, ProjectMember, group_permissions, user_groups
from app.models.user import User, UserRole


# ── /api/me/permissions ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_permissions_admin_gets_full_catalog(client: AsyncClient):
    resp = await client.get("/api/me/permissions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    # Admin gets every seeded codename
    assert "admin.user.manage" in data["granted"]
    assert "sales.lead.create" in data["granted"]
    assert "finance.journal.post" in data["granted"]
    assert data["denied"] == []


# ── Permission catalog endpoint ────────────────────────────────────


@pytest.mark.asyncio
async def test_list_permissions(client: AsyncClient):
    resp = await client.get("/api/admin/acl/permissions")
    assert resp.status_code == 200
    perms = resp.json()
    # Assert against the live catalog (it grows as features ship) and check
    # well-known anchors are present rather than freezing a count.
    from app.acl.catalog import CATALOG
    assert len(perms) == len(CATALOG)
    codenames = {p["codename"] for p in perms}
    assert "admin.group.manage" in codenames
    assert "documents.folder.manage" in codenames


# ── Group CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_group_create_and_delete(client: AsyncClient):
    resp = await client.post("/api/admin/acl/groups", json={"name": "CustomGroup", "description": "x"})
    assert resp.status_code == 201
    gid = resp.json()["id"]

    resp = await client.get("/api/admin/acl/groups")
    assert any(g["id"] == gid and g["name"] == "CustomGroup" for g in resp.json())

    resp = await client.delete(f"/api/admin/acl/groups/{gid}")
    assert resp.status_code == 204

    resp = await client.get("/api/admin/acl/groups")
    assert not any(g["id"] == gid for g in resp.json())


@pytest.mark.asyncio
async def test_group_duplicate_name_rejected(client: AsyncClient):
    await client.post("/api/admin/acl/groups", json={"name": "DupGroup"})
    resp = await client.post("/api/admin/acl/groups", json={"name": "DupGroup"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_set_group_permissions_rejects_unknown_codename(client: AsyncClient):
    resp = await client.post("/api/admin/acl/groups", json={"name": "G1"})
    gid = resp.json()["id"]
    resp = await client.put(
        f"/api/admin/acl/groups/{gid}/permissions",
        json={"codenames": ["not.a.real.code"]},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_group_permission_round_trip(client: AsyncClient):
    resp = await client.post("/api/admin/acl/groups", json={"name": "RoundTrip"})
    gid = resp.json()["id"]
    resp = await client.put(
        f"/api/admin/acl/groups/{gid}/permissions",
        json={"codenames": ["sales.lead.create", "sales.lead.view"]},
    )
    assert resp.status_code == 200
    assert sorted(resp.json()) == ["sales.lead.create", "sales.lead.view"]

    resp = await client.get(f"/api/admin/acl/groups/{gid}/permissions")
    assert sorted(resp.json()) == ["sales.lead.create", "sales.lead.view"]


# ── Resolver semantics (unit tests against db_session) ─────────────


async def _make_user(db, email: str, role: UserRole = UserRole.MEMBER) -> User:
    u = User(id=uuid.uuid4(), email=email, name=email, hashed_password="x", role=role, is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.mark.asyncio
async def test_resolver_admin_sees_every_codename(db_session):
    admin = await _make_user(db_session, "admin1@test.com", UserRole.ADMIN)
    granted, denied = await _load_effective_codes(db_session, admin)
    assert "admin.group.manage" in granted
    assert "sales.commission.manage" in granted
    assert denied == set()


@pytest.mark.asyncio
async def test_resolver_member_with_no_groups_gets_nothing(db_session):
    member = await _make_user(db_session, "m1@test.com")
    granted, denied = await _load_effective_codes(db_session, member)
    assert granted == set()
    assert denied == set()


@pytest.mark.asyncio
async def test_resolver_group_membership_grants_codenames(db_session):
    from sqlalchemy import select
    from app.models.acl import Permission

    member = await _make_user(db_session, "m2@test.com")
    group = Group(name="TestSales", description="t")
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    perm = (await db_session.scalars(select(Permission).where(Permission.codename == "sales.lead.create"))).first()
    await db_session.execute(group_permissions.insert().values(group_id=group.id, permission_id=perm.id))
    await db_session.execute(user_groups.insert().values(user_id=member.id, group_id=group.id))
    await db_session.commit()

    granted, _ = await _load_effective_codes(db_session, member)
    assert granted == {"sales.lead.create"}


@pytest.mark.asyncio
async def test_resolver_direct_deny_overrides_group_grant(db_session):
    from sqlalchemy import select
    from app.models.acl import Permission

    member = await _make_user(db_session, "m3@test.com")
    group = Group(name="SalesAll")
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    perm = (await db_session.scalars(select(Permission).where(Permission.codename == "sales.lead.create"))).first()
    await db_session.execute(group_permissions.insert().values(group_id=group.id, permission_id=perm.id))
    await db_session.execute(user_groups.insert().values(user_id=member.id, group_id=group.id))
    # Direct deny
    db_session.add(UserPermission(user_id=member.id, permission_id=perm.id, is_deny=True, reason="offboarded"))
    await db_session.commit()

    assert not await has_permission(db_session, member, "sales.lead.create")


@pytest.mark.asyncio
async def test_resolver_project_scoped_requires_membership(db_session, sample_project):
    from sqlalchemy import select
    from app.models.acl import Permission

    member = await _make_user(db_session, "m4@test.com")
    group = Group(name="PMs")
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    perm = (await db_session.scalars(select(Permission).where(Permission.codename == "projects.task.update"))).first()
    await db_session.execute(group_permissions.insert().values(group_id=group.id, permission_id=perm.id))
    await db_session.execute(user_groups.insert().values(user_id=member.id, group_id=group.id))
    await db_session.commit()

    project_id = uuid.UUID(sample_project["id"])

    # Without membership → denied despite global grant
    assert not await has_permission(db_session, member, "projects.task.update", project_id=project_id)

    # Add membership
    db_session.add(ProjectMember(project_id=project_id, user_id=member.id, role="member"))
    await db_session.commit()
    assert await has_permission(db_session, member, "projects.task.update", project_id=project_id)


@pytest.mark.asyncio
async def test_resolver_admin_bypasses_project_membership(db_session, sample_project):
    admin = await _make_user(db_session, "adm2@test.com", UserRole.ADMIN)
    project_id = uuid.UUID(sample_project["id"])
    # No ProjectMember row — admin still allowed
    assert await has_permission(db_session, admin, "projects.task.update", project_id=project_id)


# ── Enforcement: non-admin 403 ────────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_groups(db_session, client: AsyncClient):
    viewer = await _make_user(db_session, "viewer@test.com", UserRole.VIEWER)

    async def override():
        return viewer

    app.dependency_overrides[get_current_user] = override
    try:
        resp = await client.post("/api/admin/acl/groups", json={"name": "BlockedGroup"})
        assert resp.status_code == 403
    finally:
        # Restore admin override
        from tests.conftest import override_get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user


# ── Project membership endpoints ──────────────────────────────────


@pytest.mark.asyncio
async def test_project_member_crud(client: AsyncClient, sample_project):
    pid = sample_project["id"]

    # Create a user to add to the project
    from tests.conftest import async_session_test
    async with async_session_test() as s:
        uid = str(uuid.uuid4())
        s.add(User(id=uuid.UUID(uid), email="pm@test.com", name="PM", hashed_password="x", role=UserRole.MEMBER))
        await s.commit()

    resp = await client.post(f"/api/projects/{pid}/members", json={"user_id": uid, "role": "member"})
    assert resp.status_code == 201
    assert resp.json()["user_email"] == "pm@test.com"

    resp = await client.get(f"/api/projects/{pid}/members")
    assert resp.status_code == 200
    assert any(m["user_id"] == uid for m in resp.json())

    # Upsert role
    resp = await client.post(f"/api/projects/{pid}/members", json={"user_id": uid, "role": "lead"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "lead"

    # Remove
    resp = await client.delete(f"/api/projects/{pid}/members/{uid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/projects/{pid}/members")
    assert not any(m["user_id"] == uid for m in resp.json())


# ── Inspector ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inspect_explains_admin_grant(client: AsyncClient):
    from tests.conftest import _test_user_id
    resp = await client.get(
        "/api/admin/acl/inspect",
        params={"user_id": str(_test_user_id), "codename": "admin.group.manage"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert any("admin" in line for line in data["via"])


@pytest.mark.asyncio
async def test_inspect_explains_deny_for_non_member(db_session, client: AsyncClient):
    # A user with no groups, explicitly denied
    from sqlalchemy import select
    from app.models.acl import Permission

    member = await _make_user(db_session, "denied@test.com")
    perm = (await db_session.scalars(select(Permission).where(Permission.codename == "sales.lead.create"))).first()
    db_session.add(UserPermission(user_id=member.id, permission_id=perm.id, is_deny=True, reason="test"))
    await db_session.commit()

    resp = await client.get(
        "/api/admin/acl/inspect",
        params={"user_id": str(member.id), "codename": "sales.lead.create"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert any("DENIED directly" in line for line in data["via"])
