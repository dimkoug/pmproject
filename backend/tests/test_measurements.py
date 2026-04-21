import pytest
from httpx import AsyncClient


class TestCreateMeasurement:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Sprint Velocity",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sprint Velocity"
        assert data["metric_type"] == "kpi"
        assert data["domain"] == "value"
        assert data["target_value"] is None
        assert data["actual_value"] is None

    async def test_create_full(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Schedule Performance Index",
            "description": "SPI = EV / PV - measures schedule efficiency",
            "metric_type": "kpi",
            "domain": "schedule",
            "target_value": 1.0,
            "actual_value": 0.95,
            "unit": "ratio",
            "threshold_red": 0.8,
            "threshold_yellow": 0.9,
            "threshold_green": 1.0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["domain"] == "schedule"
        assert data["target_value"] == 1.0
        assert data["actual_value"] == 0.95
        assert data["unit"] == "ratio"
        assert data["threshold_red"] == 0.8

    async def test_create_all_metric_types(self, client: AsyncClient, sample_project: dict):
        types = ["kpi", "leading", "lagging", "outcome"]
        for mt in types:
            response = await client.post("/api/measurements/", json={
                "project_id": sample_project["id"],
                "name": f"Metric {mt}",
                "metric_type": mt,
            })
            assert response.status_code == 201
            assert response.json()["metric_type"] == mt

    async def test_create_all_domains(self, client: AsyncClient, sample_project: dict):
        domains = ["schedule", "cost", "quality", "scope", "risk", "stakeholder", "team", "value"]
        for dom in domains:
            response = await client.post("/api/measurements/", json={
                "project_id": sample_project["id"],
                "name": f"Metric {dom}",
                "domain": dom,
            })
            assert response.status_code == 201
            assert response.json()["domain"] == dom

    async def test_create_cost_metric(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Cost Performance Index",
            "metric_type": "kpi",
            "domain": "cost",
            "target_value": 1.0,
            "actual_value": 1.1,
            "unit": "ratio",
        })
        assert response.status_code == 201
        assert response.json()["domain"] == "cost"

    async def test_create_missing_name(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
        })
        assert response.status_code == 422

    async def test_create_invalid_metric_type(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "metric_type": "vanity",
        })
        assert response.status_code == 422

    async def test_create_invalid_domain(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "domain": "happiness",
        })
        assert response.status_code == 422


class TestListMeasurements:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/measurements/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient, sample_project: dict):
        for name in ["SPI", "CPI", "Velocity", "Defect Rate"]:
            await client.post("/api/measurements/", json={
                "project_id": sample_project["id"], "name": name,
            })
        response = await client.get(f"/api/measurements/?project_id={sample_project['id']}")
        assert len(response.json()) == 4


class TestGetMeasurement:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/measurements/", json={
            "project_id": sample_project["id"], "name": "Find Me",
        })).json()
        response = await client.get(f"/api/measurements/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Find Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/measurements/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateMeasurement:
    async def test_update_actual_value(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/measurements/", json={
            "project_id": sample_project["id"],
            "name": "Velocity",
            "target_value": 30.0,
            "actual_value": 0.0,
        })).json()
        response = await client.patch(f"/api/measurements/{created['id']}", json={"actual_value": 28.0})
        assert response.status_code == 200
        assert response.json()["actual_value"] == 28.0
        assert response.json()["target_value"] == 30.0

    async def test_update_target_value(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/measurements/", json={
            "project_id": sample_project["id"], "name": "Adjust Target",
            "target_value": 100.0,
        })).json()
        response = await client.patch(f"/api/measurements/{created['id']}", json={"target_value": 120.0})
        assert response.status_code == 200
        assert response.json()["target_value"] == 120.0

    async def test_update_domain(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/measurements/", json={
            "project_id": sample_project["id"], "name": "Domain Change",
        })).json()
        response = await client.patch(f"/api/measurements/{created['id']}", json={"domain": "quality"})
        assert response.status_code == 200
        assert response.json()["domain"] == "quality"

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/measurements/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteMeasurement:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/measurements/", json={
            "project_id": sample_project["id"], "name": "Delete Me",
        })).json()
        response = await client.delete(f"/api/measurements/{created['id']}")
        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/measurements/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
