"""End-to-end enforcement of workspace plan limits through real endpoints.

This complements test_plans.py which exercises the service layer directly.
Here we hit `/api/projects/` and `/api/workspaces/{id}/members` and assert
the 402 gate fires when the tenant is at its cap.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _new_workspace(slug: str, plan: str = "free"):
    """Create a workspace directly in the test DB and add the test user."""
    from tests.conftest import async_session_test, _test_user_id
    from app.models.cross import Workspace, WorkspaceMember
    async with async_session_test() as db:
        ws = Workspace(name=slug, slug=slug, plan=plan)
        db.add(ws); await db.commit(); await db.refresh(ws)
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=_test_user_id, role="owner"))
        await db.commit()
        return str(ws.id)


async def _override_limit(ws_id: str, **overrides):
    from tests.conftest import async_session_test
    from app.models.cross import Workspace
    from uuid import UUID
    async with async_session_test() as db:
        ws = await db.get(Workspace, UUID(ws_id))
        for k, v in overrides.items():
            setattr(ws, k, v)
        await db.commit()


class TestProjectCreateEnforcement:
    async def test_first_project_under_cap_succeeds(self, client: AsyncClient):
        ws_id = await _new_workspace("p-ok")
        r = await client.post("/api/projects/", json={
            "name": "First", "description": "", "development_approach": "agile",
            "delivery_cadence": "periodic",
        }, headers={"X-Workspace-Id": ws_id})
        assert r.status_code == 201

    async def test_over_cap_returns_402_payment_required(self, client: AsyncClient):
        ws_id = await _new_workspace("p-tight")
        # Override to 1 project allowed, then create 1 and attempt a 2nd
        await _override_limit(ws_id, max_projects=1)
        headers = {"X-Workspace-Id": ws_id}
        r1 = await client.post("/api/projects/", json={
            "name": "Alpha", "description": "", "development_approach": "agile",
            "delivery_cadence": "periodic",
        }, headers=headers)
        assert r1.status_code == 201
        r2 = await client.post("/api/projects/", json={
            "name": "Beta", "description": "", "development_approach": "agile",
            "delivery_cadence": "periodic",
        }, headers=headers)
        assert r2.status_code == 402
        detail = r2.json()["detail"]
        assert detail["limit"] == "projects"
        assert detail["cap"] == 1

    async def test_upgrading_to_pro_unlocks_creation(self, client: AsyncClient):
        ws_id = await _new_workspace("p-upgrade")
        await _override_limit(ws_id, max_projects=1)
        headers = {"X-Workspace-Id": ws_id}
        await client.post("/api/projects/", json={
            "name": "A", "description": "", "development_approach": "agile",
            "delivery_cadence": "periodic",
        }, headers=headers)
        # Bump the override up; next create should go through.
        await _override_limit(ws_id, max_projects=10)
        r = await client.post("/api/projects/", json={
            "name": "B", "description": "", "development_approach": "agile",
            "delivery_cadence": "periodic",
        }, headers=headers)
        assert r.status_code == 201


class TestWorkspaceMemberEnforcement:
    async def test_member_add_blocked_at_cap(self, client: AsyncClient):
        from tests.conftest import async_session_test
        from app.models.user import User, UserRole
        import uuid
        ws_id = await _new_workspace("m-tight")
        # Free plan: cap is 3 members total. Seed a second user so we have 2 members, then override to cap=2.
        async with async_session_test() as db:
            u2 = User(id=uuid.uuid4(), email="m2@x.com", name="M2",
                      hashed_password="x", role=UserRole.MEMBER)
            db.add(u2); await db.commit()
            u2_id = str(u2.id)
        await _override_limit(ws_id, max_users=2)
        # We already have 1 member (test user) + adding u2 makes 2 (at cap).
        # Seed a third user to try to add.
        async with async_session_test() as db:
            u3 = User(id=uuid.uuid4(), email="m3@x.com", name="M3",
                      hashed_password="x", role=UserRole.MEMBER)
            db.add(u3); await db.commit()
            u3_id = str(u3.id)
        r_add2 = await client.post(f"/api/workspaces/{ws_id}/members", json={
            "user_id": u2_id, "role": "member",
        })
        assert r_add2.status_code == 201  # brings us to 2, at cap
        r_add3 = await client.post(f"/api/workspaces/{ws_id}/members", json={
            "user_id": u3_id, "role": "member",
        })
        assert r_add3.status_code == 402
        assert r_add3.json()["detail"]["limit"] == "users"
