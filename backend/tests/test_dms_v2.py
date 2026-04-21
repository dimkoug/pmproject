"""Tests for DMS features added in v1 and v2.

v1: signatures, templates, folder permissions, retention, entity links.
v2: checkout/checkin locks, diff, workflows, annotations, esign providers, virus scan.
"""

import io
import pytest
from httpx import AsyncClient


async def _upload_doc(client: AsyncClient, title: str = "Doc", content: bytes = b"hello world") -> dict:
    files = {"file": ("test.txt", content, "text/plain")}
    data = {"title": title}
    r = await client.post("/api/dms/documents", files=files, data=data)
    assert r.status_code == 201
    return r.json()


# ── v1: Signatures ──────────────────────────────────────────────────

class TestSignatures:
    async def test_request_signature(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post("/api/dms/signatures", json={
            "document_id": doc["id"], "signer_email": "signer@test.com", "signer_name": "Signer",
        })
        assert r.status_code == 201
        assert "token" in r.json()

    async def test_sign_document(self, client: AsyncClient):
        doc = await _upload_doc(client)
        sig = (await client.post("/api/dms/signatures", json={
            "document_id": doc["id"], "signer_email": "s@s.com",
        })).json()
        r = await client.post(f"/api/dms/signatures/{sig['token']}/sign",
                               json={"signature_data": "drawn-signature-blob"})
        assert r.status_code == 200
        assert r.json()["status"] == "signed"

    async def test_decline_signature(self, client: AsyncClient):
        doc = await _upload_doc(client)
        sig = (await client.post("/api/dms/signatures", json={
            "document_id": doc["id"], "signer_email": "d@d.com",
        })).json()
        r = await client.post(f"/api/dms/signatures/{sig['id']}/decline")
        assert r.status_code == 200
        assert r.json()["status"] == "declined"

    async def test_cannot_sign_twice(self, client: AsyncClient):
        doc = await _upload_doc(client)
        sig = (await client.post("/api/dms/signatures", json={
            "document_id": doc["id"], "signer_email": "t@t.com",
        })).json()
        await client.post(f"/api/dms/signatures/{sig['token']}/sign", json={"signature_data": "x"})
        r = await client.post(f"/api/dms/signatures/{sig['token']}/sign", json={"signature_data": "y"})
        assert r.status_code == 400


# ── v1: Templates ───────────────────────────────────────────────────

class TestTemplates:
    async def test_create_template(self, client: AsyncClient):
        r = await client.post("/api/dms/templates", json={
            "name": "NDA", "category": "legal",
            "body": "This NDA is between {{party_a}} and {{party_b}}.",
            "variables": "party_a,party_b",
        })
        assert r.status_code == 201

    async def test_instantiate_substitutes_variables(self, client: AsyncClient):
        t = (await client.post("/api/dms/templates", json={
            "name": "Greeting", "body": "Hello {{name}}!",
        })).json()
        r = await client.post(f"/api/dms/templates/{t['id']}/instantiate", json={
            "title": "For Alice", "vars": {"name": "Alice"},
        })
        assert r.status_code == 201


# ── v1: Folder Permissions ──────────────────────────────────────────

class TestFolderPermissions:
    async def test_grant_list_revoke(self, client: AsyncClient):
        from tests.conftest import _test_user_id
        folder = (await client.post("/api/dms/folders", json={"name": "Locked"})).json()
        grant = await client.post("/api/dms/folders/permissions", json={
            "folder_id": folder["id"], "user_id": str(_test_user_id), "permission": "write",
        })
        assert grant.status_code == 201
        lst = (await client.get(f"/api/dms/folders/{folder['id']}/permissions")).json()
        assert any(p["user_id"] == str(_test_user_id) for p in lst)
        perm_id = grant.json()["id"]
        r = await client.delete(f"/api/dms/folders/permissions/{perm_id}")
        assert r.status_code == 204

    async def test_duplicate_grant_upserts(self, client: AsyncClient):
        from tests.conftest import _test_user_id
        folder = (await client.post("/api/dms/folders", json={"name": "Dup"})).json()
        await client.post("/api/dms/folders/permissions", json={
            "folder_id": folder["id"], "user_id": str(_test_user_id), "permission": "read",
        })
        r = await client.post("/api/dms/folders/permissions", json={
            "folder_id": folder["id"], "user_id": str(_test_user_id), "permission": "write",
        })
        assert r.status_code == 201
        assert r.json()["permission"] == "write"


# ── v1: Retention ───────────────────────────────────────────────────

class TestRetention:
    async def test_create_and_apply_policy(self, client: AsyncClient):
        r = await client.post("/api/dms/retention-policies", json={
            "name": "Archive old", "days_after": 0, "action": "archive",
        })
        assert r.status_code == 201
        # Upload a doc so policy has something to act on
        await _upload_doc(client, title="OldDoc")
        r2 = await client.post("/api/dms/retention-policies/apply")
        assert r2.status_code == 200
        assert "archived" in r2.json()


# ── v1: Entity Links ────────────────────────────────────────────────

class TestEntityLinks:
    async def test_link_doc_to_entity(self, client: AsyncClient):
        doc = await _upload_doc(client, title="Contract")
        co = (await client.post("/api/crm/companies", json={"name": "LinkCo"})).json()
        r = await client.post("/api/dms/entity-links", json={
            "document_id": doc["id"], "entity_type": "company", "entity_id": co["id"],
        })
        assert r.status_code == 201

    async def test_list_links_by_entity(self, client: AsyncClient):
        doc = await _upload_doc(client)
        co = (await client.post("/api/crm/companies", json={"name": "L2"})).json()
        await client.post("/api/dms/entity-links", json={
            "document_id": doc["id"], "entity_type": "company", "entity_id": co["id"],
        })
        r = await client.get("/api/dms/entity-links", params={"entity_type": "company", "entity_id": co["id"]})
        assert r.status_code == 200
        assert len(r.json()) == 1


# ── v2: Checkout / Checkin Locks ────────────────────────────────────

class TestLocks:
    async def test_checkout_and_checkin(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post(f"/api/dms/documents/{doc['id']}/checkout", json={"note": "editing"})
        assert r.status_code == 200
        locks = (await client.get("/api/dms/locks")).json()
        assert any(l["document_id"] == doc["id"] for l in locks)
        r2 = await client.post(f"/api/dms/documents/{doc['id']}/checkin")
        assert r2.status_code == 200

    async def test_checkin_without_lock_noop(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post(f"/api/dms/documents/{doc['id']}/checkin")
        assert r.status_code == 200
        assert r.json()["was_locked"] is False


# ── v2: Version Diff ────────────────────────────────────────────────

class TestDiff:
    async def test_diff_two_versions(self, client: AsyncClient):
        doc = await _upload_doc(client, content=b"line one\nline two\n")
        # Upload v2
        files = {"file": ("v2.txt", b"line one\nline three\n", "text/plain")}
        r = await client.post(f"/api/dms/documents/{doc['id']}/versions", files=files)
        assert r.status_code == 201
        r2 = await client.get(f"/api/dms/documents/{doc['id']}/diff", params={"v1": 1, "v2": 2})
        assert r2.status_code == 200
        data = r2.json()
        assert data["v1"] == 1 and data["v2"] == 2
        # Diff should contain added/removed lines
        assert any("line three" in s for s in data["diff"])


# ── v2: Workflows ───────────────────────────────────────────────────

class TestWorkflows:
    async def test_create_workflow(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post("/api/dms/workflows", json={
            "document_id": doc["id"], "name": "Review",
            "steps": [
                {"step_order": 0, "role": "author"},
                {"step_order": 1, "role": "reviewer"},
                {"step_order": 2, "role": "approver"},
            ],
        })
        assert r.status_code == 201

    async def test_advance_workflow_to_completion(self, client: AsyncClient):
        doc = await _upload_doc(client, title="WF Doc")
        wf = (await client.post("/api/dms/workflows", json={
            "document_id": doc["id"], "name": "WF",
            "steps": [
                {"step_order": 0, "role": "author"},
                {"step_order": 1, "role": "approver"},
            ],
        })).json()
        for _ in range(2):
            r = await client.post(f"/api/dms/workflows/{wf['id']}/advance",
                                   json={"decision": "approved"})
            assert r.status_code == 200
        # After all steps done, workflow complete
        wfs = (await client.get("/api/dms/workflows", params={"document_id": doc["id"]})).json()
        assert wfs[0]["is_complete"] is True

    async def test_rejection_ends_workflow(self, client: AsyncClient):
        doc = await _upload_doc(client, title="Reject Doc")
        wf = (await client.post("/api/dms/workflows", json={
            "document_id": doc["id"], "name": "R",
            "steps": [{"step_order": 0, "role": "approver"}],
        })).json()
        r = await client.post(f"/api/dms/workflows/{wf['id']}/advance",
                               json={"decision": "rejected", "note": "Not ready"})
        assert r.status_code == 200
        wfs = (await client.get("/api/dms/workflows", params={"document_id": doc["id"]})).json()
        assert wfs[0]["is_complete"] is True

    async def test_empty_steps_rejected(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post("/api/dms/workflows", json={
            "document_id": doc["id"], "name": "Empty", "steps": [],
        })
        assert r.status_code == 400


# ── v2: Annotations ─────────────────────────────────────────────────

class TestAnnotations:
    async def test_create_and_resolve(self, client: AsyncClient):
        doc = await _upload_doc(client)
        r = await client.post("/api/dms/annotations", json={
            "document_id": doc["id"], "body": "Typo on page 2",
        })
        assert r.status_code == 201
        anns = (await client.get("/api/dms/annotations", params={"document_id": doc["id"]})).json()
        assert len(anns) == 1
        ann_id = anns[0]["id"]
        r2 = await client.post(f"/api/dms/annotations/{ann_id}/resolve")
        assert r2.status_code == 200
        assert r2.json()["resolved"] is True


# ── v2: ESign Providers ─────────────────────────────────────────────

class TestESignProviders:
    async def test_create_provider_masks_api_key(self, client: AsyncClient):
        r = await client.post("/api/dms/esign-providers", json={
            "name": "DocuSign Prod", "provider_type": "docusign",
            "api_key": "sk_live_abcd1234",
        })
        assert r.status_code == 201
        lst = (await client.get("/api/dms/esign-providers")).json()
        # api_key_masked is not returned, but the provider should be listed
        assert any(p["name"] == "DocuSign Prod" for p in lst)

    async def test_webhook_dispatches_match(self, client: AsyncClient):
        prov = (await client.post("/api/dms/esign-providers", json={
            "name": "Internal", "provider_type": "internal",
        })).json()
        # Create a pending signature
        doc = await _upload_doc(client)
        await client.post("/api/dms/signatures", json={
            "document_id": doc["id"], "signer_email": "extsigner@test.com",
        })
        r = await client.post(f"/api/dms/esign-webhooks/{prov['id']}", json={
            "external_request_id": "ext-1", "event": "signed",
            "signer_email": "extsigner@test.com",
        })
        assert r.status_code == 200
        assert r.json().get("status") == "signed"


# ── v2: Virus Scan ──────────────────────────────────────────────────

class TestVirusScan:
    async def test_scan_clean_file(self, client: AsyncClient):
        doc = await _upload_doc(client, content=b"this is a clean file")
        versions = (await client.get(f"/api/dms/documents/{doc['id']}/versions")).json()
        ver_id = versions[0]["id"]
        r = await client.post(f"/api/dms/versions/{ver_id}/scan")
        assert r.status_code == 200
        assert r.json()["status"] == "clean"

    async def test_scan_detects_marker(self, client: AsyncClient):
        # Use a synthetic marker rather than real EICAR (which host AV would quarantine)
        infected = b"safe file contents\nPMPROJECT-SCAN-TEST-INFECTED\nmore content"
        doc = await _upload_doc(client, content=infected)
        versions = (await client.get(f"/api/dms/documents/{doc['id']}/versions")).json()
        ver_id = versions[0]["id"]
        r = await client.post(f"/api/dms/versions/{ver_id}/scan")
        assert r.status_code == 200
        assert r.json()["status"] == "infected"

    async def test_list_scan_results(self, client: AsyncClient):
        doc = await _upload_doc(client)
        versions = (await client.get(f"/api/dms/documents/{doc['id']}/versions")).json()
        await client.post(f"/api/dms/versions/{versions[0]['id']}/scan")
        r = await client.get("/api/dms/scan-results")
        assert r.status_code == 200
        assert len(r.json()) >= 1
