import pytest
from httpx import AsyncClient


class TestCreateTask:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Set up CI/CD pipeline",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Set up CI/CD pipeline"
        assert data["status"] == "backlog"
        assert data["priority"] == "medium"
        assert data["story_points"] is None
        assert data["assignee_id"] is None

    async def test_create_full(self, client: AsyncClient, sample_project: dict, sample_team_member: dict):
        response = await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Design database schema",
            "description": "Create ER diagram and implement models",
            "status": "todo",
            "priority": "high",
            "story_points": 8,
            "assignee_id": sample_team_member["id"],
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["story_points"] == 8
        assert data["assignee_id"] == sample_team_member["id"]

    async def test_create_all_statuses(self, client: AsyncClient, sample_project: dict):
        statuses = ["backlog", "todo", "in_progress", "in_review", "done", "blocked"]
        for status in statuses:
            response = await client.post("/api/tasks/", json={
                "project_id": sample_project["id"],
                "title": f"Task {status}",
                "status": status,
            })
            assert response.status_code == 201
            assert response.json()["status"] == status

    async def test_create_all_priorities(self, client: AsyncClient, sample_project: dict):
        priorities = ["critical", "high", "medium", "low"]
        for priority in priorities:
            response = await client.post("/api/tasks/", json={
                "project_id": sample_project["id"],
                "title": f"Task {priority}",
                "priority": priority,
            })
            assert response.status_code == 201
            assert response.json()["priority"] == priority

    async def test_create_missing_title(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "description": "No title",
        })
        assert response.status_code == 422

    async def test_create_invalid_status(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "status": "nonexistent",
        })
        assert response.status_code == 422

    async def test_create_invalid_priority(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Bad",
            "priority": "mega_urgent",
        })
        assert response.status_code == 422

    async def test_create_with_story_points(self, client: AsyncClient, sample_project: dict):
        for points in [1, 2, 3, 5, 8, 13, 21]:
            response = await client.post("/api/tasks/", json={
                "project_id": sample_project["id"],
                "title": f"Task {points}pt",
                "story_points": points,
            })
            assert response.status_code == 201
            assert response.json()["story_points"] == points


class TestListTasks:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/tasks/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_multiple(self, client: AsyncClient, sample_project: dict):
        for i in range(5):
            await client.post("/api/tasks/", json={
                "project_id": sample_project["id"],
                "title": f"Task {i}",
            })
        response = await client.get(f"/api/tasks/?project_id={sample_project['id']}")
        assert len(response.json()) == 5

    async def test_list_filtered_by_project(self, client: AsyncClient):
        p1 = (await client.post("/api/projects/", json={"name": "Task P1"})).json()
        p2 = (await client.post("/api/projects/", json={"name": "Task P2"})).json()
        await client.post("/api/tasks/", json={"project_id": p1["id"], "title": "T1"})
        await client.post("/api/tasks/", json={"project_id": p2["id"], "title": "T2"})
        await client.post("/api/tasks/", json={"project_id": p2["id"], "title": "T3"})

        resp1 = await client.get(f"/api/tasks/?project_id={p1['id']}")
        assert len(resp1.json()) == 1
        resp2 = await client.get(f"/api/tasks/?project_id={p2['id']}")
        assert len(resp2.json()) == 2


class TestGetTask:
    async def test_get_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"], "title": "Get Me",
        })).json()
        response = await client.get(f"/api/tasks/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateTask:
    async def test_update_status_workflow(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Workflow Task",
            "status": "backlog",
        })).json()
        tid = created["id"]
        for status in ["todo", "in_progress", "in_review", "done"]:
            response = await client.patch(f"/api/tasks/{tid}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    async def test_update_move_to_blocked(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Blocked Task",
            "status": "in_progress",
        })).json()
        response = await client.patch(f"/api/tasks/{created['id']}", json={"status": "blocked"})
        assert response.status_code == 200
        assert response.json()["status"] == "blocked"

    async def test_update_priority(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"], "title": "Prio Task",
        })).json()
        response = await client.patch(f"/api/tasks/{created['id']}", json={"priority": "critical"})
        assert response.status_code == 200
        assert response.json()["priority"] == "critical"

    async def test_update_assign_member(self, client: AsyncClient, sample_project: dict, sample_team_member: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"], "title": "Assign Task",
        })).json()
        response = await client.patch(
            f"/api/tasks/{created['id']}",
            json={"assignee_id": sample_team_member["id"]},
        )
        assert response.status_code == 200
        assert response.json()["assignee_id"] == sample_team_member["id"]

    async def test_update_story_points(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"], "title": "Points Task",
        })).json()
        response = await client.patch(f"/api/tasks/{created['id']}", json={"story_points": 13})
        assert response.status_code == 200
        assert response.json()["story_points"] == 13

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/tasks/00000000-0000-0000-0000-000000000000",
            json={"title": "Ghost"},
        )
        assert response.status_code == 404

    async def test_partial_update_preserves_fields(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"],
            "title": "Preserve Me",
            "priority": "high",
            "story_points": 5,
        })).json()
        response = await client.patch(f"/api/tasks/{created['id']}", json={"status": "in_progress"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Preserve Me"
        assert data["priority"] == "high"
        assert data["story_points"] == 5
        assert data["status"] == "in_progress"


class TestDeleteTask:
    async def test_delete_existing(self, client: AsyncClient, sample_project: dict):
        created = (await client.post("/api/tasks/", json={
            "project_id": sample_project["id"], "title": "Delete Me",
        })).json()
        response = await client.delete(f"/api/tasks/{created['id']}")
        assert response.status_code == 204
        get_resp = await client.get(f"/api/tasks/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
