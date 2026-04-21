from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, read_engine
from app.cache import get_redis, close_redis
from app.routers import (
    auth,
    projects,
    stakeholders,
    team_members,
    tasks,
    risks,
    deliverables,
    measurements,
    change_requests,
    dashboard,
    schedule,
    reports,
    comments,
    attachments,
    lessons,
    notifications,
    templates,
    features,
    advanced,
    erp,
    crm,
    dms,
    dms_public,
    cross,
    acl,
)
from app.websockets.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — serialise DDL across replicas so we never race on create_all
    from sqlalchemy import text
    _STARTUP_LOCK_KEY = 73126902
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=_STARTUP_LOCK_KEY))
        await conn.run_sync(Base.metadata.create_all)
    # Additive column migrations for existing tables (also serialised inside)
    from app.services.migrations import run_additive_migrations
    await run_additive_migrations()
    # Warm up Redis pool
    await get_redis()
    # Seed ACL catalog (idempotent, serialised by its own advisory lock)
    from app.acl.seed import seed_acl
    await seed_acl()
    yield
    # Shutdown
    await close_redis()
    await engine.dispose()
    if read_engine is not engine:
        await read_engine.dispose()


app = FastAPI(
    title="PMBOK Project Management",
    description="Project Management application based on PMBOK 7th Edition performance domains",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(stakeholders.router)
app.include_router(team_members.router)
app.include_router(tasks.router)
app.include_router(risks.router)
app.include_router(deliverables.router)
app.include_router(measurements.router)
app.include_router(change_requests.router)
app.include_router(dashboard.router)
app.include_router(schedule.router)
app.include_router(reports.router)
app.include_router(comments.router)
app.include_router(attachments.router)
app.include_router(lessons.router)
app.include_router(notifications.router)
app.include_router(templates.router)
app.include_router(features.router)
app.include_router(advanced.router)
app.include_router(erp.router)
app.include_router(crm.router)
app.include_router(dms.router)
app.include_router(dms_public.router)
app.include_router(cross.router)
app.include_router(acl.router)


@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


@app.get("/api/health")
async def health():
    """Health check — also verifies Redis connectivity."""
    info = {"status": "ok"}
    try:
        r = await get_redis()
        await r.ping()
        info["redis"] = "ok"
    except Exception:
        info["redis"] = "unavailable"
    return info
