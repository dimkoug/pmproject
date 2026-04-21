import pytest
from httpx import AsyncClient


class TestCreateStakeholder:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
            "name": "John Sponsor",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Sponsor"
        assert data["category"] == "internal"
        assert data["engagement_level"] == "neutral"
        assert data["desired_engagement"] == "supportive"
        assert data["influence"] == "medium"
        assert data["interest"] == "medium"

    async def test_create_full(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
            "name": "CEO Jane",
            "role": "Executive Sponsor",
            "email": "jane@corp.com",
            "category": "sponsor",
            "engagement_level": "leading",
            "desired_engagement": "leading",
            "influence": "high",
            "interest": "high",
            "expectations": "ROI within 12 months",
            "communication_needs": "Monthly executive report",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "sponsor"
        assert data["engagement_level"] == "leading"
        assert data["influence"] == "high"
        assert data["expectations"] == "ROI within 12 months"

    async def test_create_all_categories(self, client: AsyncClient, sample_project: dict):
        categories = ["sponsor", "customer", "end_user", "regulator", "supplier", "internal", "external"]
        for cat in categories:
            response = await client.post("/api/stakeholders/", json={
                "project_id": sample_project["id"],
                "name": f"Stakeholder {cat}",
                "category": cat,
            })
            assert response.status_code == 201
            assert response.json()["category"] == cat

    async def test_create_all_engagement_levels(self, client: AsyncClient, sample_project: dict):
        levels = ["unaware", "resistant", "neutral", "supportive", "leading"]
        for level in levels:
            response = await client.post("/api/stakeholders/", json={
                "project_id": sample_project["id"],
                "name": f"SH {level}",
                "engagement_level": level,
            })
            assert response.status_code == 201
            assert response.json()["engagement_level"] == level

    async def test_create_missing_name(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
        })
        assert response.status_code == 422

    async def test_create_invalid_category(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "category": "nonexistent",
        })
        assert response.status_code == 422

    async def test_create_invalid_engagement(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "engagement_level": "super_engaged",
        })
        assert response.status_code == 422


class TestListStakeholders:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/stakeholders/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_filtered_by_project(self, client: AsyncClient):
        p1 = (await client.post("/api/projects/", json={"name": "P1"})).json()
        p2 = (await client.post("/api/projects/", json={"name": "P2"})).json()
        await client.post("/api/stakeholders/", json={"project_id": p1["id"], "name": "SH1"})
        await client.post("/api/stakeholders/", json={"project_id": p1["id"], "name": "SH2"})
        await client.post("/api/stakeholders/", json={"project_id": p2["id"], "name": "SH3"})

        resp1 = await client.get(f"/api/stakeholders/?project_id={p1['id']}")
        assert len(resp1.json()) == 2
        resp2 = await client.get(f"/api/stakeholders/?project_id={p2['id']}")
        assert len(resp2.json()) == 1


class TestGetStakeholder:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"], "name": "Get Me",
        })).json()
        response = await client.get(f"/api/stakeholders/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/stakeholders/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateStakeholder:
    async def test_update_engagement(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"],
            "name": "Moving Engagement",
            "engagement_level": "unaware",
        })).json()
        response = await client.patch(f"/api/stakeholders/{created['id']}", json={
            "engagement_level": "supportive",
        })
        assert response.status_code == 200
        assert response.json()["engagement_level"] == "supportive"
        assert response.json()["name"] == "Moving Engagement"

    async def test_update_influence_and_interest(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"], "name": "Power Grid",
        })).json()
        response = await client.patch(f"/api/stakeholders/{created['id']}", json={
            "influence": "high",
            "interest": "low",
        })
        assert response.status_code == 200
        assert response.json()["influence"] == "high"
        assert response.json()["interest"] == "low"

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/stakeholders/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteStakeholder:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/stakeholders/", json={
            "project_id": sample_project["id"], "name": "Delete Me",
        })).json()
        response = await client.delete(f"/api/stakeholders/{created['id']}")
        assert response.status_code == 204
        get_resp = await client.get(f"/api/stakeholders/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/stakeholders/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
