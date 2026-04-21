import pytest
from httpx import AsyncClient
from app.main import app
from app.dependencies import get_current_user


class TestSignup:
    async def test_signup_success(self, client: AsyncClient):
        # Temporarily remove auth override to test real auth flow
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            response = await client.post("/api/auth/signup", json={
                "name": "New User", "email": "new@test.com", "password": "password123",
            })
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["user"]["email"] == "new@test.com"
            assert data["user"]["name"] == "New User"
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    async def test_signup_duplicate_email(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            await client.post("/api/auth/signup", json={"name": "A", "email": "dup@test.com", "password": "pass123"})
            response = await client.post("/api/auth/signup", json={"name": "B", "email": "dup@test.com", "password": "pass123"})
            assert response.status_code == 409
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    async def test_signup_missing_fields(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            response = await client.post("/api/auth/signup", json={"email": "no@name.com"})
            assert response.status_code == 422
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            await client.post("/api/auth/signup", json={"name": "Login User", "email": "login@test.com", "password": "pass123"})
            response = await client.post("/api/auth/login", json={"email": "login@test.com", "password": "pass123"})
            assert response.status_code == 200
            assert "access_token" in response.json()
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    async def test_login_wrong_password(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            await client.post("/api/auth/signup", json={"name": "WP User", "email": "wp@test.com", "password": "pass123"})
            response = await client.post("/api/auth/login", json={"email": "wp@test.com", "password": "wrong"})
            assert response.status_code == 401
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    async def test_login_nonexistent_user(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            response = await client.post("/api/auth/login", json={"email": "ghost@test.com", "password": "pass"})
            assert response.status_code == 401
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original


class TestMe:
    async def test_me_authenticated(self, client: AsyncClient):
        # With auth override active, /me should return the test user
        response = await client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@test.com"

    async def test_me_no_token(self, client: AsyncClient):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            response = await client.get("/api/auth/me")
            assert response.status_code == 401
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
