"""Integration tests for the advanced router: time entries, sprints, search,
CSV import, custom fields, dark mode, budget breakdown, baselines."""

import io
import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════════════
# Time Tracking
# ═══════════════════════════════════════════════════════════════════

class TestTimeEntries:
    async def test_create_time_entry(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Time Track Task",
        })).json()
        response = await client.post("/api/time-entries/", json={
            "project_id": pid,
            "task_id": task["id"],
            "hours": 4.5,
            "work_date": "2024-06-15",
            "description": "Worked on feature X",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["hours"] == 4.5

    async def test_list_time_entries(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "TE List Task",
        })).json()
        await client.post("/api/time-entries/", json={
            "project_id": pid, "task_id": task["id"],
            "hours": 2.0, "work_date": "2024-06-10",
        })
        await client.post("/api/time-entries/", json={
            "project_id": pid, "task_id": task["id"],
            "hours": 3.0, "work_date": "2024-06-11",
        })
        response = await client.get(f"/api/time-entries/?project_id={pid}")
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_time_summary(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Summary Task",
        })).json()
        await client.post("/api/time-entries/", json={
            "project_id": pid, "task_id": task["id"],
            "hours": 3.0, "work_date": "2024-06-10",
        })
        await client.post("/api/time-entries/", json={
            "project_id": pid, "task_id": task["id"],
            "hours": 5.0, "work_date": "2024-06-11",
        })
        response = await client.get(f"/api/time-entries/summary?project_id={pid}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_hours"] == 8.0
        assert len(data["by_task"]) >= 1


# ═══════════════════════════════════════════════════════════════════
# Sprints
# ═══════════════════════════════════════════════════════════════════

class TestSprints:
    async def test_create_sprint(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/sprints/", json={
            "project_id": sample_project["id"],
            "name": "Sprint 1",
            "goal": "Complete auth module",
            "sprint_number": 1,
            "start_date": "2024-06-01",
            "end_date": "2024-06-14",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sprint 1"

    async def test_list_sprints(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/sprints/", json={"project_id": pid, "name": "S1", "sprint_number": 1})
        await client.post("/api/sprints/", json={"project_id": pid, "name": "S2", "sprint_number": 2})
        response = await client.get(f"/api/sprints/?project_id={pid}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["sprint_number"] == 1
        assert data[1]["sprint_number"] == 2

    async def test_update_sprint_status(self, client: AsyncClient, sample_project: dict):
        sprint = (await client.post("/api/sprints/", json={
            "project_id": sample_project["id"],
            "name": "Active Sprint",
            "sprint_number": 1,
        })).json()
        response = await client.patch(f"/api/sprints/{sprint['id']}?status=active")
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    async def test_complete_sprint(self, client: AsyncClient, sample_project: dict):
        sprint = (await client.post("/api/sprints/", json={
            "project_id": sample_project["id"],
            "name": "Done Sprint",
            "sprint_number": 1,
        })).json()
        response = await client.patch(f"/api/sprints/{sprint['id']}?status=completed")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    async def test_update_nonexistent_sprint(self, client: AsyncClient):
        response = await client.patch("/api/sprints/00000000-0000-0000-0000-000000000000?status=active")
        assert response.status_code == 404

    async def test_sprint_velocity(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        # Create and complete a sprint
        sprint = (await client.post("/api/sprints/", json={
            "project_id": pid, "name": "Velocity Sprint", "sprint_number": 1,
        })).json()
        await client.patch(f"/api/sprints/{sprint['id']}?status=completed")
        response = await client.get(f"/api/sprints/velocity?project_id={pid}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


# ═══════════════════════════════════════════════════════════════════
# Global Search
# ═══════════════════════════════════════════════════════════════════

class TestSearch:
    async def test_search_tasks(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={"project_id": pid, "title": "Database Migration"})
        await client.post("/api/tasks/", json={"project_id": pid, "title": "API endpoint"})
        response = await client.get("/api/search?q=Database")
        assert response.status_code == 200
        results = response.json()
        assert any(r["title"] == "Database Migration" for r in results)

    async def test_search_risks(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/risks/", json={"project_id": pid, "title": "Security Vulnerability"})
        response = await client.get("/api/search?q=Security")
        assert response.status_code == 200
        results = response.json()
        assert any(r["type"] == "risk" and "Security" in r["title"] for r in results)

    async def test_search_projects(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/search?q={sample_project['name'][:4]}")
        assert response.status_code == 200
        results = response.json()
        assert any(r["type"] == "project" for r in results)

    async def test_search_with_project_filter(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={"project_id": pid, "title": "Filtered Search Task"})
        response = await client.get(f"/api/search?q=Filtered&project_id={pid}")
        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 1

    async def test_search_no_results(self, client: AsyncClient):
        response = await client.get("/api/search?q=zzzznonexistentzzzz")
        assert response.status_code == 200
        assert response.json() == []


# ═══════════════════════════════════════════════════════════════════
# CSV Import
# ═══════════════════════════════════════════════════════════════════

class TestCSVImport:
    async def test_import_csv(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        csv_content = (
            "title,description,status,priority,duration_days,story_points,planned_cost\n"
            "Task A,Do something,todo,high,5,3,1000\n"
            "Task B,Do other thing,backlog,medium,3,2,500\n"
        )
        response = await client.post(
            f"/api/projects/{pid}/import/csv",
            files={"file": ("tasks.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

        # Verify tasks were created
        tasks = (await client.get(f"/api/tasks/?project_id={pid}")).json()
        titles = [t["title"] for t in tasks]
        assert "Task A" in titles
        assert "Task B" in titles

    async def test_import_csv_empty_titles_skipped(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        csv_content = (
            "title,description\n"
            ",No title row\n"
            "Valid Task,Has title\n"
        )
        response = await client.post(
            f"/api/projects/{pid}/import/csv",
            files={"file": ("tasks.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1


# ═══════════════════════════════════════════════════════════════════
# Custom Fields
# ═══════════════════════════════════════════════════════════════════

class TestCustomFields:
    async def test_create_custom_field(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/custom-fields/", json={
            "project_id": sample_project["id"],
            "name": "Priority Level",
            "field_type": "select",
            "entity_type": "task",
            "options": "P0,P1,P2,P3",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Priority Level"

    async def test_list_custom_fields(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/custom-fields/", json={
            "project_id": pid, "name": "Field 1", "field_type": "text", "entity_type": "task",
        })
        await client.post("/api/custom-fields/", json={
            "project_id": pid, "name": "Field 2", "field_type": "number", "entity_type": "risk",
        })
        response = await client.get(f"/api/custom-fields/?project_id={pid}")
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_set_and_get_field_value(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        field = (await client.post("/api/custom-fields/", json={
            "project_id": pid, "name": "Severity", "field_type": "text", "entity_type": "task",
        })).json()
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "CF Task",
        })).json()

        # Set value
        response = await client.put(
            f"/api/custom-fields/{field['id']}/values/{task['id']}?value=Critical"
        )
        assert response.status_code == 200

        # Get values
        response = await client.get(f"/api/custom-fields/{field['id']}/values")
        assert response.status_code == 200
        values = response.json()
        assert values[task["id"]] == "Critical"

    async def test_update_field_value(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        field = (await client.post("/api/custom-fields/", json={
            "project_id": pid, "name": "Status Note", "field_type": "text", "entity_type": "task",
        })).json()
        task = (await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Update CF Task",
        })).json()

        await client.put(f"/api/custom-fields/{field['id']}/values/{task['id']}?value=Old")
        await client.put(f"/api/custom-fields/{field['id']}/values/{task['id']}?value=New")

        values = (await client.get(f"/api/custom-fields/{field['id']}/values")).json()
        assert values[task["id"]] == "New"


# ═══════════════════════════════════════════════════════════════════
# Dark Mode
# ═══════════════════════════════════════════════════════════════════

class TestDarkMode:
    async def test_toggle_dark_mode(self, client: AsyncClient):
        response = await client.post("/api/auth/dark-mode")
        assert response.status_code == 200
        assert "dark_mode" in response.json()

    async def test_toggle_dark_mode_returns_boolean(self, client: AsyncClient):
        response = await client.post("/api/auth/dark-mode")
        assert isinstance(response.json()["dark_mode"], bool)


# ═══════════════════════════════════════════════════════════════════
# Budget Breakdown
# ═══════════════════════════════════════════════════════════════════

class TestBudgetBreakdown:
    async def test_budget_empty_project(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/projects/{sample_project['id']}/budget")
        assert response.status_code == 200
        data = response.json()
        assert data["total_planned"] == 0
        assert data["total_actual"] == 0
        assert "by_status" in data

    async def test_budget_with_tasks(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Planned Task",
            "status": "done", "planned_cost": 5000, "actual_cost": 4500,
        })
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Active Task",
            "status": "in_progress", "planned_cost": 3000, "actual_cost": 1500,
        })
        response = await client.get(f"/api/projects/{pid}/budget")
        assert response.status_code == 200
        data = response.json()
        assert data["total_planned"] == 8000
        assert data["total_actual"] == 6000
        assert "done" in data["by_status"]
        assert "in_progress" in data["by_status"]

    async def test_budget_nonexistent_project(self, client: AsyncClient):
        response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000/budget")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Schedule Baselines
# ═══════════════════════════════════════════════════════════════════

class TestBaselines:
    async def test_list_baselines_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/projects/{sample_project['id']}/baselines")
        assert response.status_code == 200
        assert response.json() == []

    async def test_save_baseline(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Baseline Task", "duration_days": 5,
        })
        response = await client.post(
            f"/api/projects/{pid}/baselines?name=Initial%20Baseline"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Initial Baseline"
        assert "project_duration" in data

    async def test_list_baselines_after_save(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "BL Task", "duration_days": 3,
        })
        await client.post(f"/api/projects/{pid}/baselines?name=BL1")
        await client.post(f"/api/projects/{pid}/baselines?name=BL2")
        response = await client.get(f"/api/projects/{pid}/baselines")
        assert len(response.json()) == 2

    async def test_compare_baseline(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "Compare Task", "duration_days": 5,
        })
        baseline = (await client.post(
            f"/api/projects/{pid}/baselines?name=Compare%20BL"
        )).json()
        response = await client.get(
            f"/api/projects/{pid}/baselines/{baseline['id']}/compare"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["baseline_name"] == "Compare BL"
        assert "variance" in data
        assert "tasks" in data

    async def test_compare_nonexistent_baseline(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        response = await client.get(
            f"/api/projects/{pid}/baselines/00000000-0000-0000-0000-000000000000/compare"
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# Monte Carlo Endpoint
# ═══════════════════════════════════════════════════════════════════

class TestMonteCarloEndpoint:
    async def test_monte_carlo_empty_project(self, client: AsyncClient, sample_project: dict):
        response = await client.get(
            f"/api/projects/{sample_project['id']}/monte-carlo?iterations=100"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["iterations"] == 100

    async def test_monte_carlo_with_tasks(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "MC Task 1",
            "duration_days": 5, "optimistic_duration": 3,
            "most_likely_duration": 5, "pessimistic_duration": 10,
            "planned_cost": 1000,
        })
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "MC Task 2",
            "duration_days": 3, "planned_cost": 500,
        })
        response = await client.get(f"/api/projects/{pid}/monte-carlo?iterations=200")
        assert response.status_code == 200
        data = response.json()
        assert data["iterations"] == 200
        assert "duration" in data
        assert "cost" in data
        assert "histogram" in data


# ═══════════════════════════════════════════════════════════════════
# Resource Leveling Endpoint
# ═══════════════════════════════════════════════════════════════════

class TestResourceLevelingEndpoint:
    async def test_resource_leveling_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(
            f"/api/projects/{sample_project['id']}/resource-leveling"
        )
        assert response.status_code == 200
        data = response.json()
        assert "max_utilization" in data
        assert "over_allocations" in data
        assert "suggestions" in data

    async def test_resource_leveling_with_data(self, client: AsyncClient, sample_project: dict):
        pid = sample_project["id"]
        member = (await client.post("/api/team-members/", json={
            "project_id": pid, "name": "Dev A", "availability": 100,
        })).json()
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "RL Task 1",
            "duration_days": 5, "assignee_id": member["id"],
        })
        await client.post("/api/tasks/", json={
            "project_id": pid, "title": "RL Task 2",
            "duration_days": 5, "assignee_id": member["id"],
        })
        response = await client.get(f"/api/projects/{pid}/resource-leveling")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Activity Log
# ═══════════════════════════════════════════════════════════════════

class TestActivityLog:
    async def test_activity_log_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/projects/{sample_project['id']}/activity")
        assert response.status_code == 200
        assert response.json() == []
