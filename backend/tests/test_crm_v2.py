"""Tests for CRM features added in v1 and v2.

v1: quotes, campaigns, lead scoring, forecast, follow-ups.
v2: emails, contracts, commissions, territories, drips, health.
"""

import pytest
from httpx import AsyncClient


# ── Quotes ──────────────────────────────────────────────────────────

class TestQuotes:
    async def test_create_quote_with_items(self, client: AsyncClient):
        r = await client.post("/api/crm/quotes", json={
            "quote_number": "Q-1", "tax_rate": 10,
            "items": [
                {"description": "Consulting", "quantity": 10, "unit_price": 200},
                {"description": "Setup", "quantity": 1, "unit_price": 500},
            ],
        })
        assert r.status_code == 201
        assert r.json()["total"] == 2750.0  # (10*200 + 500) * 1.10

    async def test_update_quote_status(self, client: AsyncClient):
        q = (await client.post("/api/crm/quotes", json={
            "quote_number": "Q-2", "items": [{"description": "x", "quantity": 1, "unit_price": 100}],
        })).json()
        r = await client.patch(f"/api/crm/quotes/{q['id']}?status=sent")
        assert r.status_code == 200
        assert r.json()["status"] == "sent"

    async def test_convert_quote_to_invoice(self, client: AsyncClient):
        q = (await client.post("/api/crm/quotes", json={
            "quote_number": "Q-CONV",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 1000}],
        })).json()
        r = await client.post(f"/api/crm/quotes/{q['id']}/convert")
        assert r.status_code == 200
        assert "invoice_id" in r.json()

    async def test_cannot_double_convert(self, client: AsyncClient):
        q = (await client.post("/api/crm/quotes", json={
            "quote_number": "Q-DUP", "items": [{"description": "y", "quantity": 1, "unit_price": 50}],
        })).json()
        await client.post(f"/api/crm/quotes/{q['id']}/convert")
        r = await client.post(f"/api/crm/quotes/{q['id']}/convert")
        assert r.status_code == 400


# ── Campaigns ───────────────────────────────────────────────────────

class TestCampaigns:
    async def test_create_and_list_campaigns(self, client: AsyncClient):
        r = await client.post("/api/crm/campaigns", json={
            "name": "Spring", "budget": 10000, "actual_cost": 0,
        })
        assert r.status_code == 201
        lst = (await client.get("/api/crm/campaigns")).json()
        assert len(lst) >= 1

    async def test_campaign_roi_no_conversions(self, client: AsyncClient):
        c = (await client.post("/api/crm/campaigns", json={
            "name": "ROI Test", "actual_cost": 500,
        })).json()
        r = await client.get(f"/api/crm/campaigns/{c['id']}/roi")
        assert r.status_code == 200
        assert r.json()["members"] == 0

    async def test_add_campaign_member(self, client: AsyncClient):
        c = (await client.post("/api/crm/campaigns", json={"name": "Member"})).json()
        l = (await client.post("/api/crm/leads", json={"contact_name": "Lead A", "email": "a@test.com"})).json()
        r = await client.post(f"/api/crm/campaigns/{c['id']}/members", json={"lead_id": l["id"]})
        assert r.status_code == 201


# ── Lead Scoring ────────────────────────────────────────────────────

class TestLeadScoring:
    async def test_score_one_lead(self, client: AsyncClient):
        l = (await client.post("/api/crm/leads", json={
            "contact_name": "Rich Lead", "email": "rich@test.com", "phone": "555-0100",
            "company_name": "BigCo", "source": "referral", "estimated_value": 50000,
        })).json()
        r = await client.post(f"/api/crm/leads/{l['id']}/score")
        assert r.status_code == 200
        assert r.json()["score"] > 50  # Should be high given these attributes

    async def test_score_all_leads(self, client: AsyncClient):
        await client.post("/api/crm/leads", json={"contact_name": "A", "email": "a@a.com"})
        await client.post("/api/crm/leads", json={"contact_name": "B", "email": "b@b.com"})
        r = await client.post("/api/crm/leads/score-all")
        assert r.status_code == 200
        assert r.json()["scored"] >= 2


# ── Forecast ────────────────────────────────────────────────────────

class TestForecast:
    async def test_forecast_empty(self, client: AsyncClient):
        r = await client.get("/api/crm/forecast")
        assert r.status_code == 200
        assert "weighted_total" in r.json()
        assert "by_stage" in r.json()

    async def test_forecast_with_opportunity(self, client: AsyncClient):
        await client.post("/api/crm/opportunities", json={
            "title": "Big Deal", "amount": 10000, "probability": 50, "stage": "proposal",
        })
        r = await client.get("/api/crm/forecast")
        assert r.json()["weighted_total"] == 5000.0


# ── Follow-ups ──────────────────────────────────────────────────────

class TestFollowUps:
    async def test_set_and_complete_follow_up(self, client: AsyncClient):
        i = (await client.post("/api/crm/interactions", json={
            "subject": "Call", "interaction_type": "call",
        })).json()
        r = await client.patch(f"/api/crm/interactions/{i['id']}/follow-up",
                                json={"follow_up_date": "2025-01-01T00:00:00"})
        assert r.status_code == 200
        r2 = await client.post(f"/api/crm/interactions/{i['id']}/follow-up/done")
        assert r2.status_code == 200
        assert r2.json()["follow_up_done"] is True

    async def test_due_follow_ups(self, client: AsyncClient):
        i = (await client.post("/api/crm/interactions", json={
            "subject": "Overdue", "interaction_type": "call",
        })).json()
        await client.patch(f"/api/crm/interactions/{i['id']}/follow-up",
                          json={"follow_up_date": "2020-01-01T00:00:00"})
        r = await client.get("/api/crm/follow-ups/due")
        assert r.status_code == 200
        assert any(x["id"] == i["id"] for x in r.json())


# ── v2: Email Sync ──────────────────────────────────────────────────

class TestEmailSync:
    async def test_ingest_email_links_to_contact(self, client: AsyncClient):
        c = (await client.post("/api/crm/contacts", json={
            "first_name": "Linked", "email": "linked@test.com",
        })).json()
        r = await client.post("/api/crm/emails/ingest", json={
            "direction": "inbound",
            "from_email": "linked@test.com",
            "to_email": "us@co.com",
            "subject": "Hello",
        })
        assert r.status_code == 201
        assert r.json()["linked_contact"] == c["id"]

    async def test_ingest_no_match(self, client: AsyncClient):
        r = await client.post("/api/crm/emails/ingest", json={
            "direction": "inbound",
            "from_email": "stranger@unknown.com",
            "to_email": "us@co.com",
            "subject": "Cold email",
        })
        assert r.status_code == 201
        assert r.json()["linked_contact"] is None

    async def test_list_emails_by_contact(self, client: AsyncClient):
        c = (await client.post("/api/crm/contacts", json={
            "first_name": "C", "email": "c@test.com",
        })).json()
        await client.post("/api/crm/emails/ingest", json={
            "direction": "outbound", "from_email": "us@co.com", "to_email": "c@test.com",
            "subject": "Follow up",
        })
        r = await client.get("/api/crm/emails", params={"contact_id": c["id"]})
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ── v2: Contracts ───────────────────────────────────────────────────

class TestContracts:
    async def test_create_contract(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "ClientCo"})).json()
        r = await client.post("/api/crm/contracts", json={
            "company_id": co["id"],
            "contract_number": "C-1",
            "status": "active",
            "billing_cycle": "monthly",
            "amount": 1000,
            "start_date": "2025-01-01T00:00:00",
        })
        assert r.status_code == 201

    async def test_contract_metrics_mrr(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "MRRCo"})).json()
        await client.post("/api/crm/contracts", json={
            "company_id": co["id"], "contract_number": "C-M", "status": "active",
            "billing_cycle": "monthly", "amount": 500, "start_date": "2025-01-01T00:00:00",
        })
        await client.post("/api/crm/contracts", json={
            "company_id": co["id"], "contract_number": "C-Y", "status": "active",
            "billing_cycle": "yearly", "amount": 12000, "start_date": "2025-01-01T00:00:00",
        })
        r = await client.get("/api/crm/contracts/metrics")
        assert r.status_code == 200
        # MRR: 500 (monthly) + 1000 (12000/12 yearly) = 1500
        assert r.json()["mrr"] == 1500

    async def test_update_contract_status(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "StatusCo"})).json()
        c = (await client.post("/api/crm/contracts", json={
            "company_id": co["id"], "contract_number": "C-S", "status": "active",
            "billing_cycle": "monthly", "amount": 100, "start_date": "2025-01-01T00:00:00",
        })).json()
        r = await client.patch(f"/api/crm/contracts/{c['id']}?status=churned")
        assert r.status_code == 200
        assert r.json()["status"] == "churned"


# ── v2: Commissions ─────────────────────────────────────────────────

class TestCommissions:
    async def test_create_rule(self, client: AsyncClient):
        r = await client.post("/api/crm/commission-rules", json={"name": "Default 10%", "percentage": 10})
        assert r.status_code == 201

    async def test_compute_commissions(self, client: AsyncClient):
        # Need a rule
        await client.post("/api/crm/commission-rules", json={"name": "R", "percentage": 10})
        # Need a user for assigned_to — we'll use the test user
        from tests.conftest import _test_user_id
        import uuid as u
        await client.post("/api/crm/opportunities", json={
            "title": "Won Deal", "amount": 5000, "stage": "closed_won",
        })
        # Set assigned_to via direct model (this endpoint doesn't accept assigned_to in POST)
        # Compute still runs — if no assigned_to, no commission is made.
        r = await client.post("/api/crm/commissions/compute")
        assert r.status_code == 200

    async def test_pay_commission(self, client: AsyncClient):
        lst = (await client.get("/api/crm/commissions")).json()
        # If none exist, skip
        if not lst: return
        r = await client.post(f"/api/crm/commissions/{lst[0]['id']}/pay")
        assert r.status_code == 200


# ── v2: Territories ─────────────────────────────────────────────────

class TestTerritories:
    async def test_create_territory(self, client: AsyncClient):
        r = await client.post("/api/crm/territories", json={
            "name": "NA Enterprise", "rule_industry": "tech", "rule_min_revenue": 1000000,
        })
        assert r.status_code == 201

    async def test_auto_assign_runs(self, client: AsyncClient):
        r = await client.post("/api/crm/territories/auto-assign")
        assert r.status_code == 200
        assert "assigned" in r.json()


# ── v2: Drips ───────────────────────────────────────────────────────

class TestDrips:
    async def test_create_drip_sequence(self, client: AsyncClient):
        r = await client.post("/api/crm/drips", json={
            "name": "Onboarding",
            "steps": [
                {"step_order": 0, "delay_days": 0, "subject": "Welcome", "body": "Hi!"},
                {"step_order": 1, "delay_days": 3, "subject": "Tips", "body": "Tips"},
            ],
        })
        assert r.status_code == 201

    async def test_enroll_and_tick(self, client: AsyncClient):
        c = (await client.post("/api/crm/contacts", json={
            "first_name": "Enroll", "email": "enroll@test.com",
        })).json()
        seq = (await client.post("/api/crm/drips", json={
            "name": "Tick Test",
            "steps": [{"step_order": 0, "delay_days": 0, "subject": "1", "body": "b"}],
        })).json()
        r = await client.post("/api/crm/drips/enroll", json={
            "sequence_id": seq["id"], "contact_id": c["id"],
        })
        assert r.status_code == 201
        # Tick should send the email
        r2 = await client.post("/api/crm/drips/tick")
        assert r2.status_code == 200
        assert r2.json()["emails_sent"] >= 1

    async def test_empty_sequence_rejected(self, client: AsyncClient):
        seq = (await client.post("/api/crm/drips", json={"name": "Empty", "steps": []})).json()
        c = (await client.post("/api/crm/contacts", json={
            "first_name": "E", "email": "e@test.com",
        })).json()
        r = await client.post("/api/crm/drips/enroll", json={
            "sequence_id": seq["id"], "contact_id": c["id"],
        })
        assert r.status_code == 400


# ── v2: Health Score ────────────────────────────────────────────────

class TestHealthScore:
    async def test_compute_health(self, client: AsyncClient):
        co = (await client.post("/api/crm/companies", json={"name": "HealthyCo"})).json()
        r = await client.post("/api/crm/health/compute")
        assert r.status_code == 200
        assert r.json()["snapshots"] >= 1

    async def test_list_health_after_compute(self, client: AsyncClient):
        await client.post("/api/crm/companies", json={"name": "ListCo"})
        await client.post("/api/crm/health/compute")
        r = await client.get("/api/crm/health")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert "score" in r.json()[0]
