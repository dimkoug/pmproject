import pytest
from httpx import AsyncClient


class TestCreateTeamMember:
    async def test_create_minimal(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/team-members/", json={
            "project_id": sample_project["id"],
            "name": "Bob Developer",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bob Developer"
        assert data["role"] == "developer"
        assert data["availability"] == 100.0

    async def test_create_full(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/team-members/", json={
            "project_id": sample_project["id"],
            "name": "Carol Architect",
            "email": "carol@example.com",
            "role": "architect",
            "responsibilities": "System design and code reviews",
            "skills": "Python, FastAPI, React, PostgreSQL",
            "availability": 80.0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "architect"
        assert data["availability"] == 80.0
        assert data["skills"] == "Python, FastAPI, React, PostgreSQL"

    async def test_create_all_roles(self, client: AsyncClient, sample_project: dict):
        roles = [
            "project_manager", "scrum_master", "product_owner",
            "developer", "analyst", "tester", "designer", "architect", "other",
        ]
        for role in roles:
            response = await client.post("/api/team-members/", json={
                "project_id": sample_project["id"],
                "name": f"Member {role}",
                "role": role,
            })
            assert response.status_code == 201
            assert response.json()["role"] == role

    async def test_create_missing_name(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/team-members/", json={
            "project_id": sample_project["id"],
            "role": "developer",
        })
        assert response.status_code == 422

    async def test_create_invalid_role(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/team-members/", json={
            "project_id": sample_project["id"],
            "name": "Bad",
            "role": "ceo",
        })
        assert response.status_code == 422

    async def test_create_partial_availability(self, client: AsyncClient, sample_project: dict):
        response = await client.post("/api/team-members/", json={
            "project_id": sample_project["id"],
            "name": "Part Time",
            "availability": 50.0,
        })
        assert response.status_code == 201
        assert response.json()["availability"] == 50.0


class TestListTeamMembers:
    async def test_list_empty(self, client: AsyncClient, sample_project: dict):
        response = await client.get(f"/api/team-members/?project_id={sample_project['id']}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_filtered_by_project(self, client: AsyncClient):
        p1 = (await client.post("/api/projects/", json={"name": "Team P1"})).json()
        p2 = (await client.post("/api/projects/", json={"name": "Team P2"})).json()
        await client.post("/api/team-members/", json={"project_id": p1["id"], "name": "A"})
        await client.post("/api/team-members/", json={"project_id": p1["id"], "name": "B"})
        await client.post("/api/team-members/", json={"project_id": p2["id"], "name": "C"})

        resp1 = await client.get(f"/api/team-members/?project_id={p1['id']}")
        assert len(resp1.json()) == 2
        resp2 = await client.get(f"/api/team-members/?project_id={p2['id']}")
        assert len(resp2.json()) == 1


class TestGetTeamMember:
    async def test_get_existing(self, client: AsyncClient, sample_team_member: dict):
        response = await client.get(f"/api/team-members/{sample_team_member['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Alice Johnson"

    async def test_get_nonexistent(self, client: AsyncClient):
        response = await client.get("/api/team-members/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateTeamMember:
    async def test_update_role(self, client: AsyncClient, sample_team_member: dict):
        response = await client.patch(
            f"/api/team-members/{sample_team_member['id']}",
            json={"role": "scrum_master"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "scrum_master"
        assert response.json()["name"] == "Alice Johnson"

    async def test_update_availability(self, client: AsyncClient, sample_team_member: dict):
        response = await client.patch(
            f"/api/team-members/{sample_team_member['id']}",
            json={"availability": 60.0},
        )
        assert response.status_code == 200
        assert response.json()["availability"] == 60.0

    async def test_update_skills(self, client: AsyncClient, sample_team_member: dict):
        response = await client.patch(
            f"/api/team-members/{sample_team_member['id']}",
            json={"skills": "Python, Docker, Kubernetes"},
        )
        assert response.status_code == 200
        assert response.json()["skills"] == "Python, Docker, Kubernetes"

    async def test_update_nonexistent(self, client: AsyncClient):
        response = await client.patch(
            "/api/team-members/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteTeamMember:
    async def test_delete_existing(self, client: AsyncClient, sample_team_member: dict):
        response = await client.delete(f"/api/team-members/{sample_team_member['id']}")
        assert response.status_code == 204
        get_resp = await client.get(f"/api/team-members/{sample_team_member['id']}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        response = await client.delete("/api/team-members/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
