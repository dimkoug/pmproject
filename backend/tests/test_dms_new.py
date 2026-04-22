"""Tests for DMS features added in tasks #23-#32: folder-permission enforcement,
audit logging, version restore, expiry, share links, advanced search, reports.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.dependencies import get_current_user
from app.main import app
from app.models.dms import FolderPermission
from app.models.user import User, UserRole


async def _upload(client: AsyncClient, title: str, content: bytes = b"hi",
                  ct: str = "text/plain", expiry: str | None = None,
                  folder_id: str | None = None) -> dict:
    data = {"title": title}
    if expiry: data["expiry_date"] = expiry
    if folder_id: data["folder_id"] = folder_id
    r = await client.post(
        "/api/dms/documents",
        data=data,
        files={"file": (f"{title}.txt", content, ct)},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Restore version (#25) ─────────────────────────────────────────


class TestRestoreVersion:
    async def test_restore_older_version_becomes_current(self, client: AsyncClient):
        doc = await _upload(client, "Restorable", b"v1 body")
        # Upload v2
        r = await client.post(
            f"/api/dms/documents/{doc['id']}/versions",
            data={"change_notes": "second"},
            files={"file": ("v2.txt", b"v2 body", "text/plain")},
        )
        assert r.status_code == 201
        assert r.json()["version"] == 2

        # Restore v1 — should create v3 with v1's content
        r = await client.post(f"/api/dms/documents/{doc['id']}/versions/1/restore")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["current_version"] == 3
        assert body["restored_from"] == 1

        # The new version's download should yield v1 content
        r = await client.get(f"/api/dms/documents/{doc['id']}/download?version=3")
        assert r.content == b"v1 body"

    async def test_restore_unknown_version_404(self, client: AsyncClient):
        doc = await _upload(client, "X")
        r = await client.post(f"/api/dms/documents/{doc['id']}/versions/99/restore")
        assert r.status_code == 404


# ── Expiry (#27) ──────────────────────────────────────────────────


class TestExpiry:
    async def test_expiring_endpoint_lists_soon_to_expire(self, client: AsyncClient):
        soon = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        far = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        await _upload(client, "ExpSoon", expiry=soon)
        await _upload(client, "ExpFar", expiry=far)
        await _upload(client, "NoExp")

        r = await client.get("/api/dms/documents/expiring?days=7")
        assert r.status_code == 200
        titles = [d["title"] for d in r.json()]
        assert "ExpSoon" in titles
        assert "ExpFar" not in titles  # 90 days out is beyond the 7-day window
        assert "NoExp" not in titles  # no expiry at all

    async def test_patch_sets_expiry(self, client: AsyncClient):
        doc = await _upload(client, "ExpMutable")
        expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        r = await client.patch(f"/api/dms/documents/{doc['id']}?expiry_date={expiry}")
        assert r.status_code == 200
        r = await client.get("/api/dms/documents/expiring?days=14")
        titles = [d["title"] for d in r.json()]
        assert "ExpMutable" in titles


# ── Advanced search (#26) ─────────────────────────────────────────


class TestAdvancedSearch:
    async def test_search_filter_by_status(self, client: AsyncClient):
        a = await _upload(client, "AlphaStatus")
        b = await _upload(client, "BetaStatus")
        # Approve one
        await client.patch(f"/api/dms/documents/{a['id']}?status=approved")

        r = await client.get("/api/dms/search?q=Status&status=approved")
        assert r.status_code == 200
        titles = [d["title"] for d in r.json()]
        assert "AlphaStatus" in titles
        assert "BetaStatus" not in titles

    async def test_search_filter_by_file_type(self, client: AsyncClient):
        await _upload(client, "TextFile", ct="text/plain")
        await _upload(client, "PdfFile", ct="application/pdf")

        r = await client.get("/api/dms/search?q=File&file_type=application/pdf")
        titles = [d["title"] for d in r.json()]
        assert "PdfFile" in titles
        assert "TextFile" not in titles

    async def test_search_full_text(self, client: AsyncClient):
        await _upload(client, "ContentDoc", content=b"the needle in the haystack")
        r = await client.get("/api/dms/search?q=needle&full_text=true")
        assert r.status_code == 200
        assert any(d["title"] == "ContentDoc" for d in r.json())


# ── Share links (#30) ─────────────────────────────────────────────


class TestShareLinks:
    async def test_create_list_revoke_link(self, client: AsyncClient):
        doc = await _upload(client, "Shared")
        r = await client.post(f"/api/dms/documents/{doc['id']}/share", json={"expires_in_days": 7})
        assert r.status_code == 201
        body = r.json()
        token = body["token"]
        assert body["expires_at"] is not None

        r = await client.get(f"/api/dms/documents/{doc['id']}/share")
        assert len(r.json()) == 1
        link_id = r.json()[0]["id"]

        r = await client.delete(f"/api/dms/share/{link_id}")
        assert r.status_code == 204

        r = await client.get(f"/api/dms/documents/{doc['id']}/share")
        assert r.json()[0]["is_revoked"] is True

        # Public download should now refuse
        r = await client.get(f"/api/dms/share/{token}")
        assert r.status_code == 404

    async def test_public_download_works_without_auth_header(self, client: AsyncClient):
        doc = await _upload(client, "PubShared", content=b"public bytes")
        r = await client.post(f"/api/dms/documents/{doc['id']}/share", json={"expires_in_days": 1})
        token = r.json()["token"]
        r = await client.get(f"/api/dms/share/{token}")
        assert r.status_code == 200
        assert r.content == b"public bytes"

        # Download count incremented
        r = await client.get(f"/api/dms/documents/{doc['id']}/share")
        assert r.json()[0]["download_count"] == 1

    async def test_expired_link_returns_410(self, client: AsyncClient):
        from sqlalchemy import select
        from app.models.dms import DocumentShareLink
        from tests.conftest import async_session_test

        doc = await _upload(client, "SoonExpired")
        r = await client.post(f"/api/dms/documents/{doc['id']}/share", json={"expires_in_days": 1})
        token = r.json()["token"]

        # Manually expire the link in the DB
        async with async_session_test() as s:
            link = (await s.scalars(select(DocumentShareLink).where(DocumentShareLink.token == token))).first()
            link.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await s.commit()

        r = await client.get(f"/api/dms/share/{token}")
        assert r.status_code == 410

    async def test_bogus_token_returns_404(self, client: AsyncClient):
        r = await client.get("/api/dms/share/not-a-real-token")
        assert r.status_code == 404


# ── Folder permission enforcement (#23) ───────────────────────────


class TestFolderPermissionEnforcement:
    async def test_non_admin_cannot_see_private_folder(self, client: AsyncClient):
        # Admin creates a folder and grants a different user access
        folder = (await client.post("/api/dms/folders", json={"name": "Private"})).json()
        other_id = uuid.uuid4()
        # Make the "other" user exist in the DB so FK is valid
        from tests.conftest import async_session_test
        async with async_session_test() as s:
            s.add(User(id=other_id, email="other@test.com", name="Other",
                       hashed_password="x", role=UserRole.MEMBER))
            s.add(FolderPermission(folder_id=uuid.UUID(folder["id"]), user_id=other_id, permission="read"))
            await s.commit()

        # Third-party user (different from admin and from "other") — no grant
        stranger = User(
            id=uuid.uuid4(), email="stranger@test.com", name="Stranger",
            hashed_password="x", role=UserRole.MEMBER, is_active=True,
        )
        async with async_session_test() as s:
            s.add(stranger)
            await s.commit()

        async def override():
            return stranger

        app.dependency_overrides[get_current_user] = override
        try:
            r = await client.get("/api/dms/folders")
            assert r.status_code == 200
            ids = [f["id"] for f in r.json()]
            assert folder["id"] not in ids  # stranger can't see it
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user

    async def test_public_folder_visible_to_everyone(self, client: AsyncClient):
        """Folders with no FolderPermission rows are public."""
        folder = (await client.post("/api/dms/folders", json={"name": "Public"})).json()
        from tests.conftest import async_session_test
        stranger = User(
            id=uuid.uuid4(), email="stranger2@test.com", name="S2",
            hashed_password="x", role=UserRole.MEMBER, is_active=True,
        )
        async with async_session_test() as s:
            s.add(stranger)
            await s.commit()

        async def override():
            return stranger

        app.dependency_overrides[get_current_user] = override
        try:
            r = await client.get("/api/dms/folders")
            ids = [f["id"] for f in r.json()]
            assert folder["id"] in ids
        finally:
            from tests.conftest import override_get_current_user
            app.dependency_overrides[get_current_user] = override_get_current_user


# ── Audit log (#24) ───────────────────────────────────────────────


class TestAuditLog:
    async def test_upload_writes_audit_entry(self, client: AsyncClient):
        from sqlalchemy import select
        from app.models.cross import AuditEntry
        from tests.conftest import async_session_test

        doc = await _upload(client, "Audited")
        async with async_session_test() as s:
            rows = (await s.scalars(
                select(AuditEntry).where(
                    AuditEntry.domain == "dms",
                    AuditEntry.action == "upload",
                    AuditEntry.entity_id == doc["id"],
                )
            )).all()
        assert len(rows) == 1
        assert rows[0].after_data and "Audited" in rows[0].after_data

    async def test_download_writes_audit_entry(self, client: AsyncClient):
        from sqlalchemy import select
        from app.models.cross import AuditEntry
        from tests.conftest import async_session_test

        doc = await _upload(client, "DownloadMe", content=b"x")
        await client.get(f"/api/dms/documents/{doc['id']}/download")
        async with async_session_test() as s:
            rows = (await s.scalars(
                select(AuditEntry).where(
                    AuditEntry.domain == "dms",
                    AuditEntry.action == "download",
                    AuditEntry.entity_id == doc["id"],
                )
            )).all()
        assert len(rows) == 1

    async def test_delete_writes_audit_entry(self, client: AsyncClient):
        from sqlalchemy import select
        from app.models.cross import AuditEntry
        from tests.conftest import async_session_test

        doc = await _upload(client, "DeleteMe")
        r = await client.delete(f"/api/dms/documents/{doc['id']}")
        assert r.status_code == 204

        async with async_session_test() as s:
            rows = (await s.scalars(
                select(AuditEntry).where(
                    AuditEntry.domain == "dms",
                    AuditEntry.action == "delete",
                    AuditEntry.entity_id == doc["id"],
                )
            )).all()
        assert len(rows) == 1


# ── Reports (#32) ─────────────────────────────────────────────────


class TestReports:
    async def test_usage_report_ranks_top_documents(self, client: AsyncClient):
        doc = await _upload(client, "Popular")
        # Hit download 3 times
        for _ in range(3):
            await client.get(f"/api/dms/documents/{doc['id']}/download")

        r = await client.get("/api/dms/reports/usage?days=30")
        assert r.status_code == 200
        data = r.json()
        assert data["window_days"] == 30
        top_ids = [d["document_id"] for d in data["top_documents"]]
        assert doc["id"] in top_ids

    async def test_audit_report_filters_by_action(self, client: AsyncClient):
        await _upload(client, "A1")
        r = await client.get("/api/dms/reports/audit?action=upload")
        assert r.status_code == 200
        for entry in r.json():
            assert entry["action"] == "upload"

    async def test_pending_approvals_endpoint(self, client: AsyncClient):
        r = await client.get("/api/dms/reports/pending-approvals")
        assert r.status_code == 200
        data = r.json()
        assert "workflows" in data
        assert "signatures" in data
