import pytest
from httpx import AsyncClient


class TestCreateProject:
    async def test_create_project_minimal(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={"name": "Minimal Project"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"
        assert data["status"] == "initiating"
        assert data["development_approach"] == "predictive"
        assert data["delivery_cadence"] == "single"
        assert data["budget"] == 0.0
        assert data["id"] is not None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    async def test_create_project_full(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Full PMBOK Project",
            "description": "Complete project with all fields",
            "status": "planning",
            "development_approach": "hybrid",
            "delivery_cadence": "multiple",
            "budget": 500000.0,
            "vision": "Transform digital operations",
            "objectives": "Deliver 5 modules in 6 months",
            "success_criteria": "95% test coverage, all KPIs green",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full PMBOK Project"
        assert data["description"] == "Complete project with all fields"
        assert data["status"] == "planning"
        assert data["development_approach"] == "hybrid"
        assert data["delivery_cadence"] == "multiple"
        assert data["budget"] == 500000.0
        assert data["vision"] == "Transform digital operations"

    async def test_create_project_agile(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Agile Sprint Project",
            "development_approach": "agile",
            "delivery_cadence": "periodic",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["development_approach"] == "agile"
        assert data["delivery_cadence"] == "periodic"

    async def test_create_project_adaptive(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Adaptive Project",
            "development_approach": "adaptive",
        })
        assert response.status_code == 201
        assert response.json()["development_approach"] == "adaptive"

    async def test_create_project_missing_name(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={"description": "No name"})
        assert response.status_code == 422

    async def test_create_project_invalid_status(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Bad Status",
            "status": "nonexistent",
        })
        assert response.status_code == 422

    async def test_create_project_invalid_approach(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Bad Approach",
            "development_approach": "waterfall_extreme",
        })
        assert response.status_code == 422

    async def test_create_project_invalid_cadence(self, client: AsyncClient):
        response = await client.post("/api/projects/", json={
            "name": "Bad Cadence",
            "delivery_cadence": "invalid",
        })
        assert response.status_code == 422


class TestListProjects:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/projects/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient):
        await client.post("/api/projects/", json={"name": "Project A"})
        await client.post("/api/projects/", json={"name": "Project B"})
        await client.post("/api/projects/", json={"name": "Project C"})
        response = await client.get("/api/projects/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_returns_all_projects(self, client: AsyncClient):
        await client.post("/api/projects/", json={"name": "First"})
        await client.post("/api/projects/", json={"name": "Second"})
        response = await client.get("/api/projects/")
        data = response.json()
        names = {p["name"] for p in data}
        assert "First" in names
        assert "Second" in names


class TestGetProject:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_project["name"]
        assert response.json()["id"] == sample_project["id"]

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    async def test_get_invalid_uuid(self, client: AsyncClient):
        response = await client.get("/api/projects/not-a-uuid")
        assert response.status_code == 422


class TestUpdateProject:
    async def test_update_name(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["description"] == sample_project["description"]

    async def test_update_status_lifecycle(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        for status in ["planning", "executing", "monitoring", "closing", "closed"]:
            response = await client.patch(f"/api/projects/{pid}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    async def test_update_development_approach(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={"development_approach": "predictive"},
        )
        assert response.status_code == 200
        assert response.json()["development_approach"] == "predictive"

    async def test_update_budget(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={"budget": 250000.50},
        )
        assert response.status_code == 200
        assert response.json()["budget"] == 250000.50

    async def test_update_multiple_fields(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={
                "name": "Multi Update",
                "status": "executing",
                "budget": 999.99,
                "vision": "New vision",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Multi Update"
        assert data["status"] == "executing"
        assert data["budget"] == 999.99
        assert data["vision"] == "New vision"

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404

    async def test_update_invalid_status(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={"status": "imaginary"},
        )
        assert response.status_code == 422

    async def test_partial_update_preserves_fields(self, client: AsyncClient, sample_project: dict):
        response = await client.patch(
            f"/api/projects/{sample_project['id']}",
            json={"vision": "Only updating vision"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vision"] == "Only updating vision"
        assert data["name"] == sample_project["name"]
        assert data["budget"] == sample_project["budget"]


class TestDeleteProject:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        response = await client.delete(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 204
        get_resp = await client.get(f"/api/projects/{sample_project['id']}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_delete_cascade_children(self, client: AsyncClient, sample_project: dict):
        """Deleting a project should cascade-delete all child entities."""
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={"project_id": pid, "title": "Orphan task"})
        await client.post("/api/risks/", json={"project_id": pid, "title": "Orphan risk"})
        await client.post("/api/stakeholders/", json={"project_id": pid, "name": "Orphan SH"})

        response = await client.delete(f"/api/projects/{pid}")
        assert response.status_code == 204

        tasks = await client.get(f"/api/tasks/?project_id={pid}")
        assert tasks.json() == []
        risks = await client.get(f"/api/risks/?project_id={pid}")
        assert risks.json() == []
