"""Tests for cross-cutting features added in v1 and v2.

v1: company timeline, approvals, webhooks, API keys.
v2: audit log, scheduled reports, dashboard builder, SSO stub, workspaces.
"""

import pytest
from httpx import AsyncClient


# ── v1: Company Timeline ────────────────────────────────────────────

class TestCompanyTimeline:
    async def test_empty_company_timeline(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "EmptyCo"})).json()
        r = await client.get(f"/api/timeline/company/{co['id']}")
        assert r.status_code == 200
        assert r.json()["contact_count"] == 0
        assert r.json()["events"] == []

    async def test_timeline_aggregates_events(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "BusyCo"})).json()
        contact = (await client.post("/api/crm/contacts", json={
            "first_name": "B", "email": "b@busy.com", "company_id": co["id"],
        })).json()
        await client.post("/api/crm/interactions", json={
            "subject": "Meeting", "contact_id": contact["id"], "interaction_type": "meeting",
        })
        await client.post("/api/crm/opportunities", json={
            "title": "Big Opp", "company_id": co["id"], "amount": 1000,
        })
        r = await client.get(f"/api/timeline/company/{co['id']}")
        data = r.json()
        assert data["contact_count"] == 1
        # Should have interaction + opportunity events
        types = {e["type"] for e in data["events"]}
        assert "interaction" in types
        assert "opportunity" in types

    async def test_timeline_404_unknown_company(self, client: AsyncClient):
        r = await client.get("/api/timeline/company/00000000-0000-4000-8000-000000000000")
        assert r.status_code == 404


# ── v1: Approvals ───────────────────────────────────────────────────

class TestApprovals:
    async def test_create_approval(self, client: AsyncClient):
        exp = (await client.post("/api/erp/expenses", json={
            "description": "Client dinner", "amount": 500,
        })).json()
        r = await client.post("/api/approvals", json={
            "target_type": "expense", "target_id": exp["id"],
            "threshold_amount": 100,
        })
        assert r.status_code == 201
        assert r.json()["status"] == "pending"

    async def test_approve_expense_sets_is_approved(self, client: AsyncClient):
        exp = (await client.post("/api/erp/expenses", json={
            "description": "X", "amount": 50,
        })).json()
        ap = (await client.post("/api/approvals", json={
            "target_type": "expense", "target_id": exp["id"],
        })).json()
        r = await client.post(f"/api/approvals/{ap['id']}/decide",
                               json={"decision": "approved"})
        assert r.status_code == 200
        # Verify side effect
        exps = (await client.get("/api/erp/expenses")).json()
        match = next(e for e in exps if e["id"] == exp["id"])
        assert match["is_approved"] is True

    async def test_reject_approval(self, client: AsyncClient):
        exp = (await client.post("/api/erp/expenses", json={
            "description": "Reject me", "amount": 1,
        })).json()
        ap = (await client.post("/api/approvals", json={
            "target_type": "expense", "target_id": exp["id"],
        })).json()
        r = await client.post(f"/api/approvals/{ap['id']}/decide",
                               json={"decision": "rejected", "note": "Out of policy"})
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    async def test_cannot_decide_twice(self, client: AsyncClient):
        exp = (await client.post("/api/erp/expenses", json={
            "description": "Once", "amount": 1,
        })).json()
        ap = (await client.post("/api/approvals", json={
            "target_type": "expense", "target_id": exp["id"],
        })).json()
        await client.post(f"/api/approvals/{ap['id']}/decide", json={"decision": "approved"})
        r = await client.post(f"/api/approvals/{ap['id']}/decide", json={"decision": "rejected"})
        assert r.status_code == 400

    async def test_list_by_status(self, client: AsyncClient):
        r = await client.get("/api/approvals", params={"status": "pending"})
        assert r.status_code == 200


# ── v1: Webhooks ────────────────────────────────────────────────────

class TestWebhooks:
    async def test_create_webhook(self, client: AsyncClient):
        r = await client.post("/api/webhooks", json={
            "name": "Slack notify", "url": "https://hooks.example.com/test",
            "events": "invoice.paid,lead.created",
        })
        assert r.status_code == 201
        assert "secret" in r.json()

    async def test_delete_webhook(self, client: AsyncClient):
        w = (await client.post("/api/webhooks", json={
            "name": "Doomed", "url": "https://example.com",
        })).json()
        r = await client.delete(f"/api/webhooks/{w['id']}")
        assert r.status_code == 204

    async def test_list_webhooks(self, client: AsyncClient):
        await client.post("/api/webhooks", json={
            "name": "WH1", "url": "https://h1.example.com",
        })
        r = await client.get("/api/webhooks")
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ── v1: API Keys ────────────────────────────────────────────────────

class TestApiKeys:
    async def test_create_returns_plaintext_once(self, client: AsyncClient):
        r = await client.post("/api/api-keys", json={"name": "CI Key"})
        assert r.status_code == 201
        assert "api_key" in r.json()
        assert r.json()["api_key"].count(".") == 1  # prefix.raw

    async def test_revoke_api_key(self, client: AsyncClient):
        k = (await client.post("/api/api-keys", json={"name": "Revokable"})).json()
        r = await client.delete(f"/api/api-keys/{k['id']}")
        assert r.status_code == 204
        lst = (await client.get("/api/api-keys")).json()
        match = next(x for x in lst if x["id"] == k["id"])
        assert match["is_active"] is False

    async def test_list_does_not_expose_hash(self, client: AsyncClient):
        await client.post("/api/api-keys", json={"name": "Listed"})
        lst = (await client.get("/api/api-keys")).json()
        for k in lst:
            assert "key_hash" not in k
            assert "api_key" not in k


# ── v2: Audit Log ───────────────────────────────────────────────────

class TestAudit:
    async def test_log_and_query(self, client: AsyncClient):
        r = await client.post("/api/audit", json={
            "domain": "erp", "action": "create", "entity_type": "invoice",
            "entity_id": "some-id", "after_data": "{}",
        })
        assert r.status_code == 201
        lst = (await client.get("/api/audit", params={"domain": "erp"})).json()
        assert any(e["action"] == "create" for e in lst)

    async def test_filter_by_entity_type(self, client: AsyncClient):
        await client.post("/api/audit", json={
            "domain": "crm", "action": "update", "entity_type": "contact",
            "entity_id": "c1",
        })
        r = await client.get("/api/audit", params={"entity_type": "contact"})
        assert r.status_code == 200
        assert all(e["entity_type"] == "contact" for e in r.json())


# ── v2: Scheduled Reports ───────────────────────────────────────────

class TestScheduledReports:
    async def test_create_schedule(self, client: AsyncClient):
        r = await client.post("/api/scheduled-reports", json={
            "name": "Weekly CRM", "endpoint": "/api/crm/dashboard", "frequency": "weekly",
        })
        assert r.status_code == 201

    async def test_run_schedules_none_due(self, client: AsyncClient):
        # Newly created schedules have next_run in the future (1 day for daily),
        # so "run due" should return 0.
        await client.post("/api/scheduled-reports", json={
            "name": "Future", "endpoint": "/api/erp/dashboard", "frequency": "daily",
        })
        r = await client.post("/api/scheduled-reports/run")
        assert r.status_code == 200
        assert r.json()["ran"] == 0

    async def test_list_runs_empty(self, client: AsyncClient):
        s = (await client.post("/api/scheduled-reports", json={
            "name": "Runs", "endpoint": "/api/erp/dashboard", "frequency": "daily",
        })).json()
        r = await client.get(f"/api/scheduled-reports/{s['id']}/runs")
        assert r.status_code == 200
        assert r.json() == []


# ── v2: Dashboards ──────────────────────────────────────────────────

class TestDashboards:
    async def test_create_and_list(self, client: AsyncClient):
        r = await client.post("/api/dashboards", json={
            "name": "Sales Overview",
            "widgets": [{
                "title": "Pipeline", "widget_type": "stat",
                "endpoint": "/api/crm/dashboard", "json_path": "pipeline_value", "position": 0,
            }],
        })
        assert r.status_code == 201
        lst = (await client.get("/api/dashboards")).json()
        assert any(d["name"] == "Sales Overview" for d in lst)

    async def test_get_dashboard_returns_widgets(self, client: AsyncClient):
        d = (await client.post("/api/dashboards", json={
            "name": "D", "widgets": [
                {"title": "W1", "widget_type": "stat", "endpoint": "/api/erp/dashboard", "position": 0},
            ],
        })).json()
        r = await client.get(f"/api/dashboards/{d['id']}")
        assert r.status_code == 200
        assert len(r.json()["widgets"]) == 1

    async def test_add_widget(self, client: AsyncClient):
        d = (await client.post("/api/dashboards", json={"name": "Widgy", "widgets": []})).json()
        r = await client.post(f"/api/dashboards/{d['id']}/widgets", json={
            "title": "Added", "widget_type": "stat", "endpoint": "/api/erp/dashboard", "position": 1,
        })
        assert r.status_code == 201

    async def test_delete_dashboard(self, client: AsyncClient):
        d = (await client.post("/api/dashboards", json={"name": "Del", "widgets": []})).json()
        r = await client.delete(f"/api/dashboards/{d['id']}")
        assert r.status_code == 204


# ── v2: SSO (stub) ──────────────────────────────────────────────────

class TestSso:
    async def test_create_sso_provider(self, client: AsyncClient):
        r = await client.post("/api/sso/providers", json={
            "name": "Google Workspace", "provider_type": "oidc",
            "issuer_url": "https://accounts.google.com",
            "client_id": "client-id", "client_secret": "client-secret",
        })
        assert r.status_code == 201

    async def test_authorize_stub_returns_url(self, client: AsyncClient):
        p = (await client.post("/api/sso/providers", json={
            "name": "T", "provider_type": "oidc",
            "issuer_url": "https://idp.example.com", "client_id": "id",
        })).json()
        r = await client.get(f"/api/sso/authorize/{p['id']}")
        assert r.status_code == 200
        assert "authorize_url" in r.json()
        assert "stub" in r.json()["note"].lower()

    async def test_callback_stub(self, client: AsyncClient):
        p = (await client.post("/api/sso/providers", json={
            "name": "CB", "provider_type": "oidc",
        })).json()
        r = await client.post(f"/api/sso/callback/{p['id']}", params={"code": "test-code"})
        assert r.status_code == 200
        assert r.json()["code_received"] is True


# ── v2: Workspaces (stub) ───────────────────────────────────────────

class TestWorkspaces:
    async def test_create_workspace(self, client: AsyncClient):
        r = await client.post("/api/workspaces", json={
            "name": "Acme Inc", "slug": "acme", "plan": "pro",
        })
        assert r.status_code == 201

    async def test_duplicate_slug_rejected(self, client: AsyncClient):
        await client.post("/api/workspaces", json={"name": "A", "slug": "dup"})
        r = await client.post("/api/workspaces", json={"name": "B", "slug": "dup"})
        assert r.status_code == 400

    async def test_list_includes_owned(self, client: AsyncClient):
        await client.post("/api/workspaces", json={"name": "Mine", "slug": "mine"})
        r = await client.get("/api/workspaces")
        assert r.status_code == 200
        assert any(w["slug"] == "mine" for w in r.json())

    async def test_add_workspace_member(self, client: AsyncClient):
        from tests.conftest import _test_user_id
        ws = (await client.post("/api/workspaces", json={"name": "Team", "slug": "team"})).json()
        r = await client.post(f"/api/workspaces/{ws['id']}/members", json={
            "user_id": str(_test_user_id), "role": "admin",
        })
        assert r.status_code == 201
        mem = (await client.get(f"/api/workspaces/{ws['id']}/members")).json()
        assert len(mem) >= 1
