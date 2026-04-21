import pytest
from httpx import AsyncClient


class TestCompanies:
    async def test_create_company(self, client: AsyncClient):
        r = await client.post("/api/crm/companies", json={"name": "BigCorp", "industry": "Tech"})
        assert r.status_code == 201
        assert r.json()["name"] == "BigCorp"

    async def test_list_companies(self, client: AsyncClient):
        await client.post("/api/crm/companies", json={"name": "SmallCo"})
        r = await client.get("/api/crm/companies")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_delete_company(self, client: AsyncClient):
        c = (await client.post("/api/crm/companies", json={"name": "Delete Me"})).json()
        r = await client.delete(f"/api/crm/companies/{c['id']}")
        assert r.status_code == 204


class TestContacts:
    async def test_create_contact(self, client: AsyncClient):
        r = await client.post("/api/crm/contacts", json={"first_name": "John", "last_name": "Doe", "email": "john@test.com"})
        assert r.status_code == 201
        assert r.json()["first_name"] == "John"

    async def test_list_contacts(self, client: AsyncClient):
        await client.post("/api/crm/contacts", json={"first_name": "Jane"})
        r = await client.get("/api/crm/contacts")
        assert r.status_code == 200


class TestLeads:
    async def test_create_lead(self, client: AsyncClient):
        r = await client.post("/api/crm/leads", json={"contact_name": "Lead Person", "source": "referral", "estimated_value": 50000})
        assert r.status_code == 201

    async def test_update_lead_status(self, client: AsyncClient):
        l = (await client.post("/api/crm/leads", json={"contact_name": "Status Lead"})).json()
        r = await client.patch(f"/api/crm/leads/{l['id']}?status=qualified")
        assert r.status_code == 200
        assert r.json()["status"] == "qualified"


class TestOpportunities:
    async def test_create_opportunity(self, client: AsyncClient):
        r = await client.post("/api/crm/opportunities", json={"title": "Big Deal", "amount": 100000, "probability": 60})
        assert r.status_code == 201
        assert r.json()["title"] == "Big Deal"

    async def test_update_stage(self, client: AsyncClient):
        o = (await client.post("/api/crm/opportunities", json={"title": "Stage Deal"})).json()
        r = await client.patch(f"/api/crm/opportunities/{o['id']}?stage=proposal")
        assert r.status_code == 200
        assert r.json()["stage"] == "proposal"

    async def test_list_opportunities(self, client: AsyncClient):
        await client.post("/api/crm/opportunities", json={"title": "List Deal"})
        r = await client.get("/api/crm/opportunities")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestInteractions:
    async def test_create_interaction(self, client: AsyncClient):
        r = await client.post("/api/crm/interactions", json={"subject": "Follow-up call", "interaction_type": "call"})
        assert r.status_code == 201

    async def test_list_interactions(self, client: AsyncClient):
        await client.post("/api/crm/interactions", json={"subject": "Demo meeting", "interaction_type": "demo"})
        r = await client.get("/api/crm/interactions")
        assert r.status_code == 200


class TestCrmDashboard:
    async def test_dashboard(self, client: AsyncClient):
        r = await client.get("/api/crm/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "companies" in data
        assert "contacts" in data
        assert "pipeline_value" in data
        assert "pipeline_by_stage" in data
