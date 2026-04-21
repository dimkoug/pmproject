"""Integration tests for the schedule router: dependencies CRUD, CPM, PERT endpoints."""

import pytest
from httpx import AsyncClient


def _dep_payload(pid, pred_id, succ_id, dep_type="finish_to_start", lag=0):
    return {
        "project_id": pid,
        "predecessor_id": pred_id,
        "successor_id": succ_id,
        "dependency_type": dep_type,
        "lag_days": lag,
    }


class TestDependenciesCRUD:
    async def _create_two_tasks(self, client, pid):
        t1 = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Predecessor", "duration_days": 5,
        })).json()
        t2 = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Successor", "duration_days": 3,
        })).json()
        return t1, t2

    async def test_create_dependency(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t1["id"], t2["id"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["predecessor_id"] == t1["id"]
        assert data["successor_id"] == t2["id"]

    async def test_list_dependencies(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t1["id"], t2["id"]),
        )
        response = await client.get(f"/api/projects/{pid}/dependencies")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_delete_dependency(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        dep = (await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t1["id"], t2["id"]),
        )).json()
        response = await client.delete(f"/api/projects/{pid}/dependencies/{dep['id']}")
        assert response.status_code == 204

    async def test_self_dependency_rejected(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Self Task",
        })).json()
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, task["id"], task["id"]),
        )
        assert response.status_code == 400

    async def test_duplicate_dependency_rejected(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        payload = _dep_payload(pid, t1["id"], t2["id"])
        await client.post(f"/api/projects/{pid}/dependencies", json=payload)
        response = await client.post(f"/api/projects/{pid}/dependencies", json=payload)
        assert response.status_code == 409

    async def test_reverse_dependency_rejected(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t1["id"], t2["id"]),
        )
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t2["id"], t1["id"]),
        )
        assert response.status_code == 409

    async def test_circular_dependency_rejected(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1 = (await client.post("/api/tasks/", json={"project_id": pid, "title": "A", "duration_days": 1})).json()
        t2 = (await client.post("/api/tasks/", json={"project_id": pid, "title": "B", "duration_days": 1})).json()
        t3 = (await client.post("/api/tasks/", json={"project_id": pid, "title": "C", "duration_days": 1})).json()

        await client.post(f"/api/projects/{pid}/dependencies", json=_dep_payload(pid, t1["id"], t2["id"]))
        await client.post(f"/api/projects/{pid}/dependencies", json=_dep_payload(pid, t2["id"], t3["id"]))
        # This would create A->B->C->A cycle
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t3["id"], t1["id"]),
        )
        assert response.status_code == 400

    async def test_dependency_with_lag(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1, t2 = await self._create_two_tasks(client, pid)
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, t1["id"], t2["id"], lag=3),
        )
        assert response.status_code == 201
        assert response.json()["lag_days"] == 3

    async def test_nonexistent_task_dependency(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Exists",
        })).json()
        response = await client.post(
            f"/api/projects/{pid}/dependencies",
            json=_dep_payload(pid, task["id"], "00000000-0000-0000-0000-000000000000"),
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_dependency(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        response = await client.delete(
            f"/api/projects/{pid}/dependencies/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestCPMEndpoint:
    async def test_cpm_empty_project(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        response = await client.get(f"/api/projects/{pid}/cpm")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["project_duration"] == 0
        assert data["has_cycle"] is False

    async def test_cpm_sequential_tasks(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        t1 = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Design", "duration_days": 5,
        })).json()
        t2 = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Build", "duration_days": 10,
        })).json()
        t3 = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Test", "duration_days": 3,
        })).json()
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, t1["id"], t2["id"]))
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, t2["id"], t3["id"]))
        response = await client.get(f"/api/projects/{pid}/cpm")
        assert response.status_code == 200
        data = response.json()
        assert data["project_duration"] == 18  # 5+10+3
        assert data["has_cycle"] is False
        assert len(data["critical_path"]) == 3

    async def test_cpm_task_fields(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Solo", "duration_days": 7,
        })
        response = await client.get(f"/api/projects/{pid}/cpm")
        task = response.json()["tasks"][0]
        assert "es" in task
        assert "ef" in task
        assert "ls" in task
        assert "lf" in task
        assert "total_float" in task
        assert "free_float" in task
        assert "is_critical" in task

    async def test_cpm_parallel_paths(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        start = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Start", "duration_days": 2,
        })).json()
        long = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Long Path", "duration_days": 10,
        })).json()
        short = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Short Path", "duration_days": 3,
        })).json()
        end = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "End", "duration_days": 1,
        })).json()
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, start["id"], long["id"]))
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, start["id"], short["id"]))
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, long["id"], end["id"]))
        await client.post(f"/api/projects/{pid}/dependencies",
                          json=_dep_payload(pid, short["id"], end["id"]))
        response = await client.get(f"/api/projects/{pid}/cpm")
        data = response.json()
        assert data["project_duration"] == 13  # 2+10+1


class TestPERTEndpoint:
    async def test_pert_empty_project(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/projects/{sample_project['id']}/pert")
        assert response.status_code == 200
        data = response.json()
        assert data["project_expected_duration"] == 0

    async def test_pert_with_estimates(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "PERT Task",
            "optimistic_duration": 3, "most_likely_duration": 5, "pessimistic_duration": 10,
        })
        response = await client.get(f"/api/projects/{pid}/pert")
        assert response.status_code == 200
        data = response.json()
        assert data["project_expected_duration"] > 0
        task = data["tasks"][0]
        assert task["pert_expected"] is not None
        assert task["pert_std_dev"] is not None

    async def test_pert_with_target_durations(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "PERT Target",
            "optimistic_duration": 4, "most_likely_duration": 6, "pessimistic_duration": 12,
        })
        response = await client.get(
            f"/api/projects/{pid}/pert?target_durations=5,10,15,20"
        )
        assert response.status_code == 200
        probs = response.json()["completion_probabilities"]
        assert len(probs) == 4

    async def test_pert_invalid_target_durations(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Bad PERT", "duration_days": 5,
        })
        response = await client.get(
            f"/api/projects/{pid}/pert?target_durations=abc,def"
        )
        assert response.status_code == 400
