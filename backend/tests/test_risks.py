import pytest
from httpx import AsyncClient


class TestCreateRisk:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
            "title": "Server downtime risk",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Server downtime risk"
        assert data["category"] == "technical"
        assert data["probability"] == "medium"
        assert data["impact"] == "medium"
        assert data["status"] == "identified"
        assert data["strategy"] == "mitigate"

    async def test_create_full(self, client: AsyncClient, sample_project: dict, sample_team_member: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
            "title": "Key person dependency",
            "description": "Single point of failure if lead developer leaves",
            "category": "organizational",
            "probability": "high",
            "impact": "very_high",
            "status": "analyzing",
            "strategy": "mitigate",
            "response_plan": "Cross-train team members on all critical components",
            "owner_id": sample_team_member["id"],
            "trigger_conditions": "Lead developer gives notice or availability drops below 50%",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "organizational"
        assert data["probability"] == "high"
        assert data["impact"] == "very_high"
        assert data["strategy"] == "mitigate"
        assert data["owner_id"] == sample_team_member["id"]
        assert "Cross-train" in data["response_plan"]

    async def test_create_all_categories(self, client: AsyncClient, sample_project: dict):
        categories = ["technical", "external", "organizational", "project_management"]
        for cat in categories:
            response = await client.post("/api/risks/", json={
                "project_id": sample_project["id"],
                "title": f"Risk {cat}",
                "category": cat,
            })
            assert response.status_code == 201
            assert response.json()["category"] == cat

    async def test_create_all_probabilities(self, client: AsyncClient, sample_project: dict):
        probs = ["very_low", "low", "medium", "high", "very_high"]
        for prob in probs:
            response = await client.post("/api/risks/", json={
                "project_id": sample_project["id"],
                "title": f"Risk prob {prob}",
                "probability": prob,
            })
            assert response.status_code == 201
            assert response.json()["probability"] == prob

    async def test_create_all_impacts(self, client: AsyncClient, sample_project: dict):
        impacts = ["very_low", "low", "medium", "high", "very_high"]
        for imp in impacts:
            response = await client.post("/api/risks/", json={
                "project_id": sample_project["id"],
                "title": f"Risk impact {imp}",
                "impact": imp,
            })
            assert response.status_code == 201
            assert response.json()["impact"] == imp

    async def test_create_all_strategies(self, client: AsyncClient, sample_project: dict):
        strategies = ["avoid", "mitigate", "transfer", "accept", "escalate", "exploit", "enhance", "share"]
        for strat in strategies:
            response = await client.post("/api/risks/", json={
                "project_id": sample_project["id"],
                "title": f"Risk {strat}",
                "strategy": strat,
            })
            assert response.status_code == 201
            assert response.json()["strategy"] == strat

    async def test_create_missing_title(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
        })
        assert response.status_code == 422

    async def test_create_invalid_category(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "category": "financial",
        })
        assert response.status_code == 422

    async def test_create_invalid_probability(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "probability": "ultra_high",
        })
        assert response.status_code == 422

    async def test_create_invalid_strategy(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/risks/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "strategy": "pray",
        })
        assert response.status_code == 422


class TestListRisks:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/risks/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient, sample_project: dict):
        for i in range(4):
            await client.post("/api/risks/", json={
                "project_id": sample_project["id"],
                "title": f"Risk {i}",
            })
        response = await client.get(f"/api/risks/?project_id={sample_project['id']}")
        assert len(response.json()) == 4


class TestGetRisk:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Find Me",
        })).json()
        response = await client.get(f"/api/risks/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Find Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/risks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateRisk:
    async def test_update_status_lifecycle(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Lifecycle Risk",
        })).json()
        rid = created["id"]
        for status in ["analyzing", "planned", "active", "resolved", "closed"]:
            response = await client.patch(f"/api/risks/{rid}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    async def test_update_probability_and_impact(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Update P/I",
        })).json()
        response = await client.patch(f"/api/risks/{created['id']}", json={
            "probability": "very_high",
            "impact": "very_high",
        })
        assert response.status_code == 200
        assert response.json()["probability"] == "very_high"
        assert response.json()["impact"] == "very_high"

    async def test_update_strategy(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Strategy Change",
        })).json()
        response = await client.patch(f"/api/risks/{created['id']}", json={"strategy": "avoid"})
        assert response.status_code == 200
        assert response.json()["strategy"] == "avoid"

    async def test_update_response_plan(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Plan Change",
        })).json()
        response = await client.patch(f"/api/risks/{created['id']}", json={
            "response_plan": "Implement fallback server architecture",
        })
        assert response.status_code == 200
        assert "fallback" in response.json()["response_plan"]

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/risks/00000000-0000-0000-0000-000000000000",
            json={"title": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteRisk:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/risks/", json={
            "project_id": sample_project["id"], "title": "Delete Me",
        })).json()
        response = await client.delete(f"/api/risks/{created['id']}")
        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/risks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
