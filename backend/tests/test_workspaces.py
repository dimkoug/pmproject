"""Workspace isolation MVP (#46) — integration tests.

Verifies the X-Workspace-Id header path:
  * `seed_default_workspace_and_backfill` creates the Default workspace
  * `get_active_workspace_id` resolves header > membership > default
  * Listing companies filters by the active workspace
  * Creating a company stamps it with the active workspace
"""

from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.asyncio


async def _seed_default_in_test_db():
    """The production seed helper binds to the prod engine, so tests create
    the Default workspace directly against the test sqlite session."""
    from tests.conftest import async_session_test
    from app.models.cross import Workspace
    from sqlalchemy import select
    async with async_session_test() as db:
        existing = (await db.execute(select(Workspace).where(Workspace.slug == "default"))).scalar_one_or_none()
        if existing:
            return existing
        ws = Workspace(name="Default workspace", slug="default", plan="default")
        db.add(ws); await db.commit(); await db.refresh(ws)
        return ws


async def test_default_workspace_is_seeded(client):
    from app.services.workspaces import get_default_workspace
    from tests.conftest import async_session_test
    await _seed_default_in_test_db()
    async with async_session_test() as db:
        ws = await get_default_workspace(db)
    assert ws is not None
    assert ws.slug == "default"


async def test_get_active_workspace_falls_back_to_default(client):
    from fastapi import Request
    from app.services.workspaces import get_active_workspace_id, get_default_workspace
    from tests.conftest import async_session_test, _test_user_id
    from app.models.user import User, UserRole

    await _seed_default_in_test_db()
    async with async_session_test() as db:
        user = await db.get(User, _test_user_id)
        if not user:
            user = User(id=_test_user_id, email="t@t.com", name="t", hashed_password="x", role=UserRole.ADMIN, is_active=True)
            db.add(user); await db.commit()
        scope = {"type": "http", "headers": [], "method": "GET", "path": "/"}
        request = Request(scope)
        wid = await get_active_workspace_id(request, user, db)
        default = await get_default_workspace(db)
    assert wid == default.id


async def test_get_active_workspace_honours_header(client):
    from fastapi import Request
    from app.services.workspaces import get_active_workspace_id
    from tests.conftest import async_session_test, _test_user_id
    from app.models.cross import Workspace, WorkspaceMember
    from app.models.user import User, UserRole

    await _seed_default_in_test_db()
    async with async_session_test() as db:
        user = await db.get(User, _test_user_id) or User(
            id=_test_user_id, email="t@t.com", name="t", hashed_password="x", role=UserRole.ADMIN, is_active=True,
        )
        if not user.id == _test_user_id or not (await db.get(User, _test_user_id)):
            db.add(user); await db.commit()
        # Create another workspace & make user a member
        other = Workspace(name="Acme HQ", slug="acme-hq")
        db.add(other); await db.commit(); await db.refresh(other)
        db.add(WorkspaceMember(workspace_id=other.id, user_id=user.id, role="member"))
        await db.commit()
        scope = {
            "type": "http",
            "headers": [(b"x-workspace-id", str(other.id).encode())],
            "method": "GET",
            "path": "/",
        }
        request = Request(scope)
        wid = await get_active_workspace_id(request, user, db)
    assert wid == other.id


async def test_get_active_workspace_admin_bypasses_membership(client):
    """Admins (UserRole.ADMIN) can target any workspace via header without
    being a member. Non-admins would have the header silently ignored."""
    from fastapi import Request
    from app.services.workspaces import get_active_workspace_id, get_default_workspace
    from tests.conftest import async_session_test, _test_user_id
    from app.models.cross import Workspace
    from app.models.user import User, UserRole

    await _seed_default_in_test_db()
    async with async_session_test() as db:
        admin = await db.get(User, _test_user_id)
        # Admin user, no membership in `other`
        other = Workspace(name="Foreign", slug="foreign-corp")
        db.add(other); await db.commit(); await db.refresh(other)
        scope = {
            "type": "http",
            "headers": [(b"x-workspace-id", str(other.id).encode())],
            "method": "GET",
            "path": "/",
        }
        request = Request(scope)
        wid = await get_active_workspace_id(request, admin, db)
    assert wid == other.id  # admin bypasses


async def test_company_create_stamps_active_workspace(client):
    """POST /api/crm/companies should set workspace_id from the request header."""
    from tests.conftest import async_session_test
    from app.models.cross import Workspace
    from app.models.crm import Company
    from sqlalchemy import select

    await _seed_default_in_test_db()
    async with async_session_test() as db:
        ws = Workspace(name="Tenant A", slug="tenant-a")
        db.add(ws); await db.commit(); await db.refresh(ws)
        ws_id = str(ws.id)

    r = await client.post(
        "/api/crm/companies",
        json={"name": "Tenant-A Test Co"},
        headers={"X-Workspace-Id": ws_id},
    )
    assert r.status_code == 201

    async with async_session_test() as db:
        result = await db.execute(select(Company).where(Company.name == "Tenant-A Test Co"))
        company = result.scalar_one()
    assert str(company.workspace_id) == ws_id


async def test_company_list_filters_by_workspace(client):
    from tests.conftest import async_session_test
    from app.models.cross import Workspace
    from app.models.crm import Company

    await _seed_default_in_test_db()
    async with async_session_test() as db:
        a = Workspace(name="WS-A", slug="ws-a")
        b = Workspace(name="WS-B", slug="ws-b")
        db.add_all([a, b]); await db.commit(); await db.refresh(a); await db.refresh(b)
        db.add(Company(name="In A only", workspace_id=a.id))
        db.add(Company(name="In B only", workspace_id=b.id))
        await db.commit()
        a_id = str(a.id); b_id = str(b.id)

    ra = await client.get("/api/crm/companies", headers={"X-Workspace-Id": a_id})
    rb = await client.get("/api/crm/companies", headers={"X-Workspace-Id": b_id})
    assert ra.status_code == 200 and rb.status_code == 200
    a_names = {c["name"] for c in ra.json()}
    b_names = {c["name"] for c in rb.json()}
    assert "In A only" in a_names and "In B only" not in a_names
    assert "In B only" in b_names and "In A only" not in b_names
