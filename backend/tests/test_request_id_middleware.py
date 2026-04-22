"""Phase 4 #4 — request-id propagation middleware."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRequestIdHeader:
    async def test_generates_id_when_missing(self, client: AsyncClient):
        r = await client.get("/api/health")
        assert "x-request-id" in {h.lower() for h in r.headers.keys()}
        rid = r.headers.get("X-Request-Id") or r.headers.get("x-request-id")
        assert rid
        assert 8 <= len(rid) <= 64

    async def test_echoes_client_supplied_id(self, client: AsyncClient):
        r = await client.get("/api/health", headers={"X-Request-Id": "my-trace-001"})
        # Middleware echoes the client-provided request id
        echoed = r.headers.get("X-Request-Id") or r.headers.get("x-request-id")
        assert echoed == "my-trace-001"

    async def test_each_request_gets_unique_id(self, client: AsyncClient):
        r1 = await client.get("/api/health")
        r2 = await client.get("/api/health")
        id1 = r1.headers.get("X-Request-Id") or r1.headers.get("x-request-id")
        id2 = r2.headers.get("X-Request-Id") or r2.headers.get("x-request-id")
        assert id1 != id2
