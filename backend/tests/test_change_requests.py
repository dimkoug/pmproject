import pytest
from httpx import AsyncClient


class TestCreateChangeRequest:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"],
            "title": "Add OAuth2 support",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Add OAuth2 support"
        assert data["status"] == "submitted"
        assert data["impact"] == "medium"

    async def test_create_full(self, client: AsyncClient, sample_project: dict, sample_team_member: dict):
        response = await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"],
            "title": "Migrate from REST to GraphQL",
            "description": "Replace REST API layer with GraphQL for better client flexibility",
            "justification": "Client team requires flexible queries, REST over-fetching costs 30% extra bandwidth",
            "impact": "high",
            "impact_analysis": "Requires 3 sprints, affects all frontend components, needs team training",
            "requested_by_id": sample_team_member["id"],
        })
        assert response.status_code == 201
        data = response.json()
        assert data["impact"] == "high"
        assert data["requested_by_id"] == sample_team_member["id"]
        assert "GraphQL" in data["description"]
        assert "3 sprints" in data["impact_analysis"]

    async def test_create_all_impacts(self, client: AsyncClient, sample_project: dict):
        impacts = ["low", "medium", "high", "critical"]
        for impact in impacts:
            response = await client.post("/api/change-requests/", json={
                "project_id": sample_project["id"],
                "title": f"CR impact {impact}",
                "impact": impact,
            })
            assert response.status_code == 201
            assert response.json()["impact"] == impact

    async def test_create_missing_title(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"],
        })
        assert response.status_code == 422

    async def test_create_invalid_impact(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "impact": "nuclear",
        })
        assert response.status_code == 422

    async def test_create_invalid_status(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "status": "auto_approved",
        })
        assert response.status_code == 422


class TestListChangeRequests:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/change-requests/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient, sample_project: dict):
        for i in range(4):
            await client.post("/api/change-requests/", json={
                "project_id": sample_project["id"],
                "title": f"CR {i}",
            })
        response = await client.get(f"/api/change-requests/?project_id={sample_project['id']}")
        assert len(response.json()) == 4

    async def test_list_filtered_by_project(self, client: AsyncClient):
        p1 = (await client.post("/api/projects/", json={"name": "CR P1"})).json()
        p2 = (await client.post("/api/projects/", json={"name": "CR P2"})).json()
        await client.post("/api/change-requests/", json={"project_id": p1["id"], "title": "CR1"})
        await client.post("/api/change-requests/", json={"project_id": p2["id"], "title": "CR2"})
        await client.post("/api/change-requests/", json={"project_id": p2["id"], "title": "CR3"})

        resp1 = await client.get(f"/api/change-requests/?project_id={p1['id']}")
        assert len(resp1.json()) == 1
        resp2 = await client.get(f"/api/change-requests/?project_id={p2['id']}")
        assert len(resp2.json()) == 2


class TestGetChangeRequest:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Find Me",
        })).json()
        response = await client.get(f"/api/change-requests/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Find Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/change-requests/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateChangeRequest:
    async def test_update_status_approval_workflow(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Workflow CR",
        })).json()
        crid = created["id"]
        for status in ["under_review", "approved", "implemented"]:
            response = await client.patch(f"/api/change-requests/{crid}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    async def test_update_status_rejection_workflow(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Reject CR",
        })).json()
        crid = created["id"]
        response = await client.patch(f"/api/change-requests/{crid}", json={"status": "under_review"})
        assert response.status_code == 200
        response = await client.patch(f"/api/change-requests/{crid}", json={"status": "rejected"})
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    async def test_update_status_deferred(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Defer CR",
        })).json()
        response = await client.patch(f"/api/change-requests/{created['id']}", json={"status": "deferred"})
        assert response.status_code == 200
        assert response.json()["status"] == "deferred"

    async def test_update_impact_analysis(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Analysis CR",
        })).json()
        response = await client.patch(f"/api/change-requests/{created['id']}", json={
            "impact_analysis": "Affects schedule by 2 weeks, budget increase of $10k",
        })
        assert response.status_code == 200
        assert "2 weeks" in response.json()["impact_analysis"]

    async def test_update_reviewer(self, client: AsyncClient, sample_project: dict, sample_team_member: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Review CR",
        })).json()
        response = await client.patch(f"/api/change-requests/{created['id']}", json={
            "reviewed_by_id": sample_team_member["id"],
            "status": "under_review",
        })
        assert response.status_code == 200
        assert response.json()["reviewed_by_id"] == sample_team_member["id"]

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/change-requests/00000000-0000-0000-0000-000000000000",
            json={"title": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteChangeRequest:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/change-requests/", json={
            "project_id": sample_project["id"], "title": "Delete Me",
        })).json()
        response = await client.delete(f"/api/change-requests/{created['id']}")
        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/change-requests/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
