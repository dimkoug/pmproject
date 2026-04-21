import pytest
from httpx import AsyncClient


class TestCreateDeliverable:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "API Documentation",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Documentation"
        assert data["status"] == "planned"
        assert data["quality_level"] == "not_assessed"
        assert data["completion_percentage"] == 0.0

    async def test_create_full(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "User Authentication Module",
            "description": "Complete auth system with OAuth2 support",
            "status": "in_progress",
            "quality_level": "meets_standard",
            "acceptance_criteria": "All auth flows pass E2E tests, security audit completed",
            "completion_percentage": 65.0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["quality_level"] == "meets_standard"
        assert data["completion_percentage"] == 65.0
        assert "OAuth2" in data["description"]

    async def test_create_all_statuses(self, client: AsyncClient, sample_project: dict):
        statuses = ["planned", "in_progress", "ready_for_review", "accepted", "rejected"]
        for status in statuses:
            response = await client.post("/api/deliverables/", json={
                "project_id": sample_project["id"],
                "name": f"Del {status}",
                "status": status,
            })
            assert response.status_code == 201
            assert response.json()["status"] == status

    async def test_create_all_quality_levels(self, client: AsyncClient, sample_project: dict):
        levels = ["not_assessed", "below_standard", "meets_standard", "exceeds_standard"]
        for level in levels:
            response = await client.post("/api/deliverables/", json={
                "project_id": sample_project["id"],
                "name": f"Del quality {level}",
                "quality_level": level,
            })
            assert response.status_code == 201
            assert response.json()["quality_level"] == level

    async def test_create_missing_name(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
        })
        assert response.status_code == 422

    async def test_create_invalid_status(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "status": "shipped",
        })
        assert response.status_code == 422

    async def test_create_completion_boundary_0(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "Zero",
            "completion_percentage": 0.0,
        })
        assert response.status_code == 201
        assert response.json()["completion_percentage"] == 0.0

    async def test_create_completion_boundary_100(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "Full",
            "completion_percentage": 100.0,
        })
        assert response.status_code == 201
        assert response.json()["completion_percentage"] == 100.0


class TestListDeliverables:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/deliverables/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient, sample_project: dict):
        for i in range(3):
            await client.post("/api/deliverables/", json={
                "project_id": sample_project["id"],
                "name": f"Deliverable {i}",
            })
        response = await client.get(f"/api/deliverables/?project_id={sample_project['id']}")
        assert len(response.json()) == 3


class TestGetDeliverable:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"], "name": "Find Me",
        })).json()
        response = await client.get(f"/api/deliverables/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Find Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/deliverables/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateDeliverable:
    async def test_update_status(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"], "name": "Status Del",
        })).json()
        did = created["id"]
        for status in ["in_progress", "ready_for_review", "accepted"]:
            response = await client.patch(f"/api/deliverables/{did}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    async def test_update_quality(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"], "name": "Quality Del",
        })).json()
        response = await client.patch(f"/api/deliverables/{created['id']}", json={
            "quality_level": "exceeds_standard",
        })
        assert response.status_code == 200
        assert response.json()["quality_level"] == "exceeds_standard"

    async def test_update_completion_progress(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"], "name": "Progress Del",
        })).json()
        did = created["id"]
        for pct in [10.0, 25.0, 50.0, 75.0, 100.0]:
            response = await client.patch(f"/api/deliverables/{did}", json={"completion_percentage": pct})
            assert response.status_code == 200
            assert response.json()["completion_percentage"] == pct

    async def test_update_rejected_deliverable(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"],
            "name": "Rejected Del",
            "status": "ready_for_review",
        })).json()
        response = await client.patch(f"/api/deliverables/{created['id']}", json={"status": "rejected"})
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/deliverables/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteDeliverable:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/deliverables/", json={
            "project_id": sample_project["id"], "name": "Delete Me",
        })).json()
        response = await client.delete(f"/api/deliverables/{created['id']}")
        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/deliverables/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
