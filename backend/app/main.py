import asyncio
import json
import logging
import time
import uuid as _uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import Base, engine, read_engine
from app.cache import get_redis, close_redis
from app.config import settings as _settings

# Sentry (#17) — best-effort init. No-op when SDK isn't installed or DSN unset.
if _settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        sentry_sdk.init(
            dsn=_settings.sentry_dsn,
            environment=_settings.sentry_environment,
            traces_sample_rate=_settings.sentry_traces_sample_rate,
            integrations=[FastApiIntegration(), StarletteIntegration()],
            send_default_pii=False,
        )
    except Exception as _e:
        logging.getLogger(__name__).warning("Sentry init skipped: %s", _e)
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
    exports,
    presence,
    tags,
    automation,
    hr,
    gdpr,
    sso,
    stripe_webhooks,
    shipping,
    portal,
    ai_plan,
    semantic,
    workspaces,
    trash,
    email_admin,
    pricing,
    onboarding,
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
    # Seed Default workspace + backfill flagship tables (#46)
    from app.services.workspaces import seed_default_workspace_and_backfill
    await seed_default_workspace_and_backfill()
    yield
    # Shutdown — graceful drain. Stop accepting new requests, give the
    # in-flight ones up to 8s to finish before tearing down clients.
    drain_seconds = float(getattr(__import__("os").environ, "GRACEFUL_DRAIN_SECONDS", "8") or 8)
    if hasattr(app.state, "_inflight"):
        deadline = asyncio.get_event_loop().time() + drain_seconds
        while app.state._inflight > 0 and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.1)
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

# Prometheus — expose /metrics with per-handler latency histograms
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        excluded_handlers=["/metrics", "/api/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except ImportError:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Structured logging + request-id propagation ────────────────────
# JSON log line per request (status, latency, request id) — grep-friendly at
# scale. The X-Request-Id header is propagated to the response so traces can
# be stitched across services.

_access_logger = logging.getLogger("app.access")
if not _access_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    _access_logger.addHandler(_h)
    _access_logger.setLevel(logging.INFO)
    _access_logger.propagate = False


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or _uuid.uuid4().hex[:16]
        request.state.request_id = rid
        # Inflight counter for graceful drain on shutdown
        request.app.state._inflight = getattr(request.app.state, "_inflight", 0) + 1
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            request.app.state._inflight -= 1
            try:
                _access_logger.info(json.dumps({
                    "ts": time.time(),
                    "rid": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "ms": duration_ms,
                    "ip": request.client.host if request.client else None,
                }, default=str))
            except Exception:
                pass
        response.headers["X-Request-Id"] = rid
        return response


app.state._inflight = 0
app.add_middleware(RequestIdMiddleware)


# ── Per-user rate limit (#20) ──────────────────────────────────────
# Redis-backed sliding-window-ish counter. Limits per authenticated user
# rather than per IP (nginx already does per-IP). Unauth requests fall
# through to nginx's limiter alone.

class PerUserRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip for non-api paths, health, metrics, webhooks (they auth by signature)
        path = request.url.path
        if not path.startswith("/api/") or path in ("/api/health",) or path.startswith("/api/webhooks/"):
            return await call_next(request)
        token = request.headers.get("Authorization", "")
        if not token.lower().startswith("bearer "):
            return await call_next(request)
        limit = _settings.per_user_rate_limit_rpm
        if limit <= 0:
            return await call_next(request)
        # Derive user-id from token without full auth round-trip (cheap decode, no verify)
        try:
            import base64 as _b64, json as _json
            payload_b64 = token.split(" ", 1)[1].split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            claims = _json.loads(_b64.urlsafe_b64decode(payload_b64))
            uid = claims.get("sub")
        except Exception:
            return await call_next(request)
        if not uid:
            return await call_next(request)
        try:
            r = await get_redis()
            # Bucket per user per minute
            bucket_key = f"rl:u:{uid}:{int(time.time() // 60)}"
            count = await r.incr(bucket_key)
            if count == 1:
                await r.expire(bucket_key, 65)
            if count > limit:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "limit": limit, "retry_after_seconds": 60},
                    headers={"Retry-After": "60"},
                )
        except Exception:
            # Redis down — fail open rather than blocking legitimate traffic
            pass
        return await call_next(request)


app.add_middleware(PerUserRateLimitMiddleware)

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
app.include_router(exports.router)
app.include_router(presence.router)
app.include_router(tags.router)
app.include_router(automation.router)
app.include_router(hr.router)
app.include_router(gdpr.router)
app.include_router(sso.router)
app.include_router(stripe_webhooks.router)
app.include_router(shipping.router)
app.include_router(shipping.webhook_router)
app.include_router(portal.admin_router)
app.include_router(portal.public_router)
app.include_router(ai_plan.router)
app.include_router(semantic.router)
app.include_router(workspaces.router)
app.include_router(trash.router)
app.include_router(email_admin.admin_router)
app.include_router(email_admin.track_router)
app.include_router(pricing.router)
app.include_router(pricing.returns_router)
app.include_router(onboarding.router)


@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


@app.get("/api/health")
async def health(response: Response):
    """Liveness + dependency check.

    Returns 200 when every dependency answers, 503 when any one fails. Each
    check is best-effort with a tight timeout so an outage on one tier doesn't
    drag the response time of the health endpoint."""
    import asyncio
    info: dict = {"status": "ok"}
    failures: list[str] = []

    # DB
    try:
        async def _db_check():
            from sqlalchemy import text
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        await asyncio.wait_for(_db_check(), timeout=2.0)
        info["db"] = "ok"
    except Exception:
        info["db"] = "unavailable"
        failures.append("db")

    # Redis cache
    try:
        async def _redis_check():
            r = await get_redis()
            await r.ping()
        await asyncio.wait_for(_redis_check(), timeout=1.0)
        info["redis"] = "ok"
    except Exception:
        info["redis"] = "unavailable"
        failures.append("redis")

    if failures:
        info["status"] = "degraded"
        info["failed"] = failures
        response.status_code = 503
    return info
