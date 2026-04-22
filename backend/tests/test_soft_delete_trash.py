"""Soft delete + Trash router (Phase 1 #7 / #22)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProjectSoftDelete:
    async def test_delete_sets_deleted_at_instead_of_removing(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code == 204

        from tests.conftest import async_session_test
        from app.models.project import Project
        from uuid import UUID
        async with async_session_test() as db:
            row = await db.get(Project, UUID(pid))
        # Row still exists — only deleted_at is set
        assert row is not None
        assert row.deleted_at is not None

    async def test_listing_excludes_soft_deleted(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        await client.delete(f"/api/projects/{pid}")
        r = await client.get("/api/projects/")
        ids = {p["id"] for p in r.json()}
        assert pid not in ids


class TestTrashRouter:
    async def test_trash_lists_soft_deleted_projects(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        await client.delete(f"/api/projects/{pid}")
        r = await client.get("/api/admin/trash")
        assert r.status_code == 200
        rows = r.json()
        assert any(row["entity"] == "project" and row["id"] == pid for row in rows)

    async def test_trash_filters_by_entity_type(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        await client.delete(f"/api/projects/{pid}")
        # Filter to just projects
        r = await client.get("/api/admin/trash?entity=project")
        assert all(row["entity"] == "project" for row in r.json())
        # Filter to companies — project shouldn't appear
        r2 = await client.get("/api/admin/trash?entity=company")
        assert not any(row["id"] == pid for row in r2.json())

    async def test_restore_unsets_deleted_at(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        await client.delete(f"/api/projects/{pid}")
        r = await client.post(f"/api/admin/trash/project/{pid}/restore")
        assert r.status_code in (200, 204)

        from tests.conftest import async_session_test
        from app.models.project import Project
        from uuid import UUID
        async with async_session_test() as db:
            row = await db.get(Project, UUID(pid))
        assert row.deleted_at is None

    async def test_purge_actually_removes(self, client: AsyncClient, sample_project):
        pid = sample_project["id"]
        await client.delete(f"/api/projects/{pid}")
        r = await client.delete(f"/api/admin/trash/project/{pid}")
        assert r.status_code == 204

        from tests.conftest import async_session_test
        from app.models.project import Project
        from uuid import UUID
        async with async_session_test() as db:
            row = await db.get(Project, UUID(pid))
        assert row is None

    async def test_unknown_entity_type_400(self, client: AsyncClient):
        r = await client.post("/api/admin/trash/banana/00000000-0000-4000-8000-000000000000/restore")
        assert r.status_code in (400, 404)
