"""Workspace plan limits (Phase 3 #8).

Covers:
  * PLANS catalog has the 3 known tiers
  * `get_effective_limits` resolves per-row overrides over plan defaults
  * `check_can_add_member` / `check_can_add_project` raise 402 at the cap
  * `/api/me/workspaces/plans` + `/api/me/workspaces/{id}/usage` endpoints
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace():
    """Create a workspace on the free plan and add the test user as a member."""
    from tests.conftest import async_session_test, _test_user_id
    from app.models.cross import Workspace, WorkspaceMember
    async with async_session_test() as db:
        ws = Workspace(name="Plans Test Co", slug="plans-test", plan="free")
        db.add(ws); await db.commit(); await db.refresh(ws)
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=_test_user_id, role="owner"))
        await db.commit()
        return {"id": ws.id, "id_str": str(ws.id), "plan": ws.plan}


class TestPlanCatalog:
    def test_known_tiers_exist(self):
        from app.services.plans import PLANS
        assert set(PLANS.keys()) == {"free", "pro", "enterprise"}

    def test_free_is_tighter_than_pro(self):
        from app.services.plans import PLANS
        assert PLANS["free"].max_users < PLANS["pro"].max_users
        assert PLANS["free"].max_projects < PLANS["pro"].max_projects
        assert PLANS["free"].max_storage_mb < PLANS["pro"].max_storage_mb

    def test_enterprise_caps_are_very_high(self):
        from app.services.plans import PLANS
        # Enterprise is effectively unbounded for normal customers.
        assert PLANS["enterprise"].max_users >= 1000
        assert PLANS["enterprise"].max_projects >= 1000


class TestEffectiveLimits:
    async def test_falls_back_to_plan_defaults(self, workspace):
        from tests.conftest import async_session_test
        from app.services.plans import get_effective_limits, PLANS
        async with async_session_test() as db:
            limits = await get_effective_limits(db, workspace["id"])
        assert limits.max_users == PLANS["free"].max_users
        assert limits.max_projects == PLANS["free"].max_projects

    async def test_per_row_override_wins(self, workspace):
        from tests.conftest import async_session_test
        from app.services.plans import get_effective_limits
        from app.models.cross import Workspace
        async with async_session_test() as db:
            ws = await db.get(Workspace, workspace["id"])
            ws.max_users = 99
            ws.max_projects = 77
            await db.commit()
            limits = await get_effective_limits(db, workspace["id"])
        assert limits.max_users == 99
        assert limits.max_projects == 77

    async def test_unknown_workspace_returns_free_limits(self):
        from tests.conftest import async_session_test
        from app.services.plans import get_effective_limits, PLANS
        import uuid
        async with async_session_test() as db:
            limits = await get_effective_limits(db, uuid.uuid4())
        assert limits == PLANS["free"]


class TestPlanEnforcement:
    async def test_add_project_fails_at_free_cap(self, workspace):
        from tests.conftest import async_session_test
        from app.services.plans import check_can_add_project, PLANS
        from app.models.project import Project
        from app.models.project import DevelopmentApproach, DeliveryCadence
        from fastapi import HTTPException
        # Seed enough projects to hit the free cap
        async with async_session_test() as db:
            for i in range(PLANS["free"].max_projects):
                db.add(Project(
                    name=f"p{i}", workspace_id=workspace["id"],
                    development_approach=DevelopmentApproach.AGILE,
                    delivery_cadence=DeliveryCadence.PERIODIC,
                ))
            await db.commit()

            with pytest.raises(HTTPException) as exc_info:
                await check_can_add_project(db, workspace["id"])
            assert exc_info.value.status_code == 402
            assert exc_info.value.detail["error"] == "plan_limit_reached"
            assert exc_info.value.detail["limit"] == "projects"

    async def test_under_cap_does_not_raise(self, workspace):
        from tests.conftest import async_session_test
        from app.services.plans import check_can_add_project
        async with async_session_test() as db:
            # No projects yet — free cap allows 2, should pass.
            await check_can_add_project(db, workspace["id"])  # no raise


class TestPlanEndpoints:
    async def test_plans_catalog_endpoint(self, client: AsyncClient):
        r = await client.get("/api/me/workspaces/plans")
        assert r.status_code == 200
        body = r.json()
        assert {"free", "pro", "enterprise"}.issubset(body.keys())
        assert body["free"]["max_users"] >= 1
        assert body["pro"]["max_users"] > body["free"]["max_users"]

    async def test_usage_endpoint_returns_caps_and_current(self, client: AsyncClient, workspace):
        r = await client.get(f"/api/me/workspaces/{workspace['id_str']}/usage")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"limits", "usage", "remaining"}
        assert body["usage"]["users"] >= 1  # the test user
        assert body["limits"]["max_users"] >= 1

    async def test_usage_endpoint_rejects_non_member(self, client: AsyncClient):
        """A non-admin user cannot read usage for a workspace they're not in.
        Here our test user IS admin so they can, but we verify the membership
        path by monkeypatching the user role to MEMBER."""
        from tests.conftest import async_session_test, _test_user_id
        from app.models.user import User, UserRole
        from app.models.cross import Workspace
        # Create a workspace the test user is NOT a member of
        async with async_session_test() as db:
            ws = Workspace(name="Foreign", slug="foreign-pl")
            db.add(ws); await db.commit(); await db.refresh(ws)
            fid = str(ws.id)
            user = await db.get(User, _test_user_id)
            user.role = UserRole.MEMBER
            await db.commit()
        try:
            r = await client.get(f"/api/me/workspaces/{fid}/usage")
            assert r.status_code == 403
        finally:
            async with async_session_test() as db:
                user = await db.get(User, _test_user_id)
                user.role = UserRole.ADMIN
                await db.commit()
