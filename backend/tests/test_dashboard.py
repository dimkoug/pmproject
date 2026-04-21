import pytest
from httpx import AsyncClient


class TestDashboardEmpty:
    async def test_dashboard_empty_project(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/dashboard/{sample_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_stats"] == {}
        assert data["risk_stats"] == {}
        assert data["deliverable_stats"] == {}
        assert data["stakeholder_count"] == 0
        assert data["team_count"] == 0
        assert data["change_request_count"] == 0
        assert data["measurements"] == []


class TestDashboardTaskStats:
    async def test_task_distribution(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T1", "status": "backlog"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T2", "status": "backlog"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T3", "status": "in_progress"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T4", "status": "done"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T5", "status": "done"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T6", "status": "done"})

        response = await client.get(f"/api/dashboard/{pid}")
        data = response.json()
        assert data["task_stats"]["backlog"] == 2
        assert data["task_stats"]["in_progress"] == 1
        assert data["task_stats"]["done"] == 3

    async def test_all_task_statuses_in_dashboard(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        statuses = ["backlog", "todo", "in_progress", "in_review", "done", "blocked"]
        for s in statuses:
            await client.post("/api/tasks/", json={"project_id": pid, "title": f"T {s}", "status": s})
        response = await client.get(f"/api/dashboard/{pid}")
        stats = response.json()["task_stats"]
        for s in statuses:
            assert stats[s] == 1


class TestDashboardRiskStats:
    async def test_risk_distribution(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/risks/", json={"project_id": pid, "title": "R1", "status": "identified"})
        await client.post("/api/risks/", json={"project_id": pid, "title": "R2", "status": "identified"})
        await client.post("/api/risks/", json={"project_id": pid, "title": "R3", "status": "active"})
        await client.post("/api/risks/", json={"project_id": pid, "title": "R4", "status": "resolved"})

        response = await client.get(f"/api/dashboard/{pid}")
        data = response.json()
        assert data["risk_stats"]["identified"] == 2
        assert data["risk_stats"]["active"] == 1
        assert data["risk_stats"]["resolved"] == 1


class TestDashboardDeliverableStats:
    async def test_deliverable_distribution(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/deliverables/", json={"project_id": pid, "name": "D1", "status": "planned"})
        await client.post("/api/deliverables/", json={"project_id": pid, "name": "D2", "status": "in_progress"})
        await client.post("/api/deliverables/", json={"project_id": pid, "name": "D3", "status": "accepted"})

        response = await client.get(f"/api/dashboard/{pid}")
        data = response.json()
        assert data["deliverable_stats"]["planned"] == 1
        assert data["deliverable_stats"]["in_progress"] == 1
        assert data["deliverable_stats"]["accepted"] == 1


class TestDashboardCounts:
    async def test_stakeholder_count(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        for i in range(5):
            await client.post("/api/stakeholders/", json={"project_id": pid, "name": f"SH{i}"})
        response = await client.get(f"/api/dashboard/{pid}")
        assert response.json()["stakeholder_count"] == 5

    async def test_team_count(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        for i in range(3):
            await client.post("/api/team-members/", json={"project_id": pid, "name": f"TM{i}"})
        response = await client.get(f"/api/dashboard/{pid}")
        assert response.json()["team_count"] == 3

    async def test_change_request_count(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        for i in range(2):
            await client.post("/api/change-requests/", json={"project_id": pid, "title": f"CR{i}"})
        response = await client.get(f"/api/dashboard/{pid}")
        assert response.json()["change_request_count"] == 2


class TestDashboardMeasurements:
    async def test_measurements_in_dashboard(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/measurements/", json={
            "project_id": pid,
            "name": "Velocity",
            "domain": "team",
            "target_value": 30,
            "actual_value": 28,
            "unit": "points",
        })
        await client.post("/api/measurements/", json={
            "project_id": pid,
            "name": "CPI",
            "domain": "cost",
            "target_value": 1.0,
            "actual_value": 0.95,
            "unit": "ratio",
        })
        response = await client.get(f"/api/dashboard/{pid}")
        measurements = response.json()["measurements"]
        assert len(measurements) == 2
        names = [m["name"] for m in measurements]
        assert "Velocity" in names
        assert "CPI" in names

    async def test_measurements_limit_10(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        for i in range(15):
            await client.post("/api/measurements/", json={
                "project_id": pid, "name": f"Metric {i}",
            })
        response = await client.get(f"/api/dashboard/{pid}")
        measurements = response.json()["measurements"]
        assert len(measurements) == 10

    async def test_measurement_fields_in_dashboard(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/measurements/", json={
            "project_id": pid,
            "name": "SPI",
            "domain": "schedule",
            "target_value": 1.0,
            "actual_value": 0.85,
            "unit": "ratio",
        })
        response = await client.get(f"/api/dashboard/{pid}")
        m = response.json()["measurements"][0]
        assert "id" in m
        assert m["name"] == "SPI"
        assert m["domain"] == "schedule"
        assert m["target_value"] == 1.0
        assert m["actual_value"] == 0.85
        assert m["unit"] == "ratio"


class TestDashboardFullProject:
    async def test_full_project_dashboard(self, client: AsyncClient, sample_project: dict):
        """Simulate a realistic project with data in all domains."""
        pid = sample_project["id"]

        # Stakeholders
        for name in ["Sponsor", "Customer", "Regulator"]:
            await client.post("/api/stakeholders/", json={"project_id": pid, "name": name})

        # Team
        for name in ["PM", "Dev1", "Dev2", "Tester"]:
            await client.post("/api/team-members/", json={"project_id": pid, "name": name})

        # Tasks
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T1", "status": "done"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T2", "status": "done"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T3", "status": "in_progress"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "T4", "status": "todo"})

        # Risks
        await client.post("/api/risks/", json={"project_id": pid, "title": "R1", "status": "active"})
        await client.post("/api/risks/", json={"project_id": pid, "title": "R2", "status": "resolved"})

        # Deliverables
        await client.post("/api/deliverables/", json={"project_id": pid, "name": "D1", "status": "accepted"})
        await client.post("/api/deliverables/", json={"project_id": pid, "name": "D2", "status": "in_progress"})

        # Measurements
        await client.post("/api/measurements/", json={
            "project_id": pid, "name": "SPI", "domain": "schedule",
            "target_value": 1.0, "actual_value": 0.92, "unit": "ratio",
        })

        # Change requests
        await client.post("/api/change-requests/", json={"project_id": pid, "title": "CR1"})

        response = await client.get(f"/api/dashboard/{pid}")
        assert response.status_code == 200
        data = response.json()
        assert data["stakeholder_count"] == 3
        assert data["team_count"] == 4
        assert data["task_stats"]["done"] == 2
        assert data["task_stats"]["in_progress"] == 1
        assert data["task_stats"]["todo"] == 1
        assert data["risk_stats"]["active"] == 1
        assert data["risk_stats"]["resolved"] == 1
        assert data["deliverable_stats"]["accepted"] == 1
        assert data["deliverable_stats"]["in_progress"] == 1
        assert data["change_request_count"] == 1
        assert len(data["measurements"]) == 1
