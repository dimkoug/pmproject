import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.acl.catalog import CATALOG
from app.database import Base, get_db
from app.dependencies import get_current_user
from app.models.acl import Permission
from app.models.user import User, UserRole
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session_test = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_test() as session:
        yield session


_test_user_id = uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d")


async def override_get_current_user():
    async with async_session_test() as session:
        user = await session.get(User, _test_user_id)
        if user:
            return user
    return User(id=_test_user_id, email="test@test.com", name="Test User",
                hashed_password="fake", role=UserRole.ADMIN, is_active=True)


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed the ACL catalog so require_permission() succeeds (admin enumerates
    # all permissions; an empty catalog would block every gated endpoint).
    # Also insert the admin test user so FK references work.
    async with async_session_test() as session:
        existing = await session.get(User, _test_user_id)
        if not existing:
            session.add(User(
                id=_test_user_id, email="test@test.com", name="Test User",
                hashed_password="fake", role=UserRole.ADMIN, is_active=True,
            ))
        for spec in CATALOG:
            session.add(Permission(
                codename=spec.codename, name=spec.name,
                description=spec.description, category=spec.category,
            ))
        await session.commit()
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_test() as session:
        yield session


@pytest.fixture
async def sample_project(client: AsyncClient) -> dict:
    response = await client.post("/api/projects/", json={
        "name": "Test PMBOK Project",
        "description": "A test project based on PMBOK 7th Edition",
        "development_approach": "agile",
        "delivery_cadence": "periodic",
        "budget": 100000.0,
        "vision": "Deliver value through iterative development",
        "objectives": "Complete all 8 performance domains",
        "success_criteria": "All deliverables accepted",
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def sample_team_member(client: AsyncClient, sample_project: dict) -> dict:
    response = await client.post("/api/team-members/", json={
        "project_id": sample_project["id"],
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "role": "project_manager",
        "responsibilities": "Overall project coordination",
        "skills": "Leadership, Risk management, Agile",
        "availability": 100.0,
    })
    assert response.status_code == 201
    return response.json()
