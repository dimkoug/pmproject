"""Onboarding wizard (Phase 3 #9)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestOnboardingStatus:
    async def test_initial_status_for_fresh_user(self, client: AsyncClient):
        r = await client.get("/api/onboarding/status")
        assert r.status_code == 200
        body = r.json()
        # All 5 steps declared
        assert len(body["steps"]) == 5
        keys = {s["key"] for s in body["steps"]}
        assert keys == {"welcome", "profile", "workspace", "first_project", "invite"}
        assert body["skipped"] is False
        assert body["finished"] is False

    async def test_remaining_complement_to_completed(self, client: AsyncClient):
        r = await client.get("/api/onboarding/status")
        body = r.json()
        assert set(body["completed"]).isdisjoint(set(body["remaining"]))
        assert len(body["completed"]) + len(body["remaining"]) == len(body["steps"])


class TestCompleteStep:
    async def test_unknown_step_rejected(self, client: AsyncClient):
        r = await client.post("/api/onboarding/steps/does_not_exist")
        assert r.status_code == 400

    async def test_completing_welcome_marks_it_done(self, client: AsyncClient):
        r = await client.post("/api/onboarding/steps/welcome")
        assert r.status_code == 200
        assert "welcome" in r.json()["completed"]

    async def test_idempotent_complete(self, client: AsyncClient):
        """Completing twice is harmless — the key just stays in the set."""
        await client.post("/api/onboarding/steps/profile")
        r = await client.post("/api/onboarding/steps/profile")
        assert r.json()["completed"].count("profile") == 1

    async def test_all_steps_complete_finishes_wizard(self, client: AsyncClient):
        for key in ("welcome", "profile", "workspace", "first_project", "invite"):
            await client.post(f"/api/onboarding/steps/{key}")
        r = await client.get("/api/onboarding/status")
        body = r.json()
        assert body["finished"] is True
        assert body["show_wizard"] is False


class TestSkip:
    async def test_skip_hides_wizard(self, client: AsyncClient):
        await client.post("/api/onboarding/skip")
        r = await client.get("/api/onboarding/status")
        body = r.json()
        assert body["skipped"] is True
        assert body["show_wizard"] is False


class TestAutoDetect:
    async def test_existing_workspace_membership_auto_completes(self, client: AsyncClient):
        """If the user is already a workspace member, `workspace` step flips to
        done automatically on the next status fetch."""
        from tests.conftest import async_session_test, _test_user_id
        from app.models.cross import Workspace, WorkspaceMember
        async with async_session_test() as db:
            ws = Workspace(name="Auto WS", slug="auto-ws")
            db.add(ws); await db.commit(); await db.refresh(ws)
            db.add(WorkspaceMember(workspace_id=ws.id, user_id=_test_user_id, role="member"))
            await db.commit()

        r = await client.get("/api/onboarding/status")
        assert "workspace" in r.json()["completed"]

    async def test_existing_project_auto_completes_first_project(self, client: AsyncClient, sample_project):
        r = await client.get("/api/onboarding/status")
        assert "first_project" in r.json()["completed"]


class TestAdminReset:
    async def test_reset_clears_state(self, client: AsyncClient):
        from tests.conftest import _test_user_id
        await client.post("/api/onboarding/steps/welcome")
        await client.post("/api/onboarding/skip")
        r = await client.post(f"/api/onboarding/reset/{_test_user_id}")
        assert r.status_code == 200
        # After reset status should show empty completed + not skipped
        body = (await client.get("/api/onboarding/status")).json()
        assert body["skipped"] is False
        assert body["finished"] is False
        # (completed may still include auto-detected steps; welcome was cleared)
        assert "welcome" not in body["completed"]

    async def test_non_admin_reset_forbidden(self, client: AsyncClient):
        from tests.conftest import async_session_test, _test_user_id
        from app.models.user import User, UserRole
        async with async_session_test() as db:
            u = await db.get(User, _test_user_id)
            u.role = UserRole.MEMBER
            await db.commit()
        try:
            r = await client.post(f"/api/onboarding/reset/{_test_user_id}")
            assert r.status_code == 403
        finally:
            async with async_session_test() as db:
                u = await db.get(User, _test_user_id)
                u.role = UserRole.ADMIN
                await db.commit()
