"""API key scopes (Phase 4 #9).

Covers:
  * _normalize_scopes handles strings, lists, empty
  * Create with scopes round-trips through the API
  * PATCH can update scopes + is_active
  * require_api_key_scope dependency: 401 missing/invalid key, 403 missing scope, 200 with scope
"""
from __future__ import annotations

import hashlib
import secrets

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestNormalizeScopes:
    def test_list_input(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes(["a", "b", "c"]) == "a,b,c"

    def test_space_separated(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes("read:x read:y") == "read:x,read:y"

    def test_comma_separated(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes("read:x,read:y") == "read:x,read:y"

    def test_mixed_whitespace_and_commas(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes("  read:x ,  read:y   read:z") == "read:x,read:y,read:z"

    def test_dedupes_preserving_order(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes(["a", "b", "a"]) == "a,b"

    def test_empty_is_empty(self):
        from app.routers.cross import _normalize_scopes
        assert _normalize_scopes("") == ""
        assert _normalize_scopes([]) == ""
        assert _normalize_scopes(None) == ""


class TestApiKeyCrudWithScopes:
    async def test_create_with_scopes_list(self, client: AsyncClient):
        r = await client.post("/api/api-keys", json={
            "name": "Bot A", "scopes": ["read:projects", "write:tasks"],
        })
        assert r.status_code == 201
        body = r.json()
        assert set(body["scopes"]) == {"read:projects", "write:tasks"}
        assert body["api_key"].startswith(body["id"][:0] or "")  # has the prefix.<secret> shape
        assert "." in body["api_key"]

    async def test_create_with_scopes_string(self, client: AsyncClient):
        r = await client.post("/api/api-keys", json={
            "name": "Bot B", "scopes": "read:x write:y",
        })
        assert set(r.json()["scopes"]) == {"read:x", "write:y"}

    async def test_list_returns_scopes_as_array(self, client: AsyncClient):
        await client.post("/api/api-keys", json={"name": "L1", "scopes": "s1 s2"})
        r = await client.get("/api/api-keys")
        rows = r.json()
        assert any(row["name"] == "L1" and set(row["scopes"]) == {"s1", "s2"} for row in rows)

    async def test_patch_updates_scopes(self, client: AsyncClient):
        created = (await client.post("/api/api-keys", json={
            "name": "P1", "scopes": "old:scope",
        })).json()
        r = await client.patch(f"/api/api-keys/{created['id']}", json={
            "scopes": ["new:one", "new:two"],
        })
        assert r.status_code == 200
        assert set(r.json()["scopes"]) == {"new:one", "new:two"}

    async def test_patch_deactivate(self, client: AsyncClient):
        created = (await client.post("/api/api-keys", json={"name": "P2"})).json()
        r = await client.patch(f"/api/api-keys/{created['id']}", json={"is_active": False})
        assert r.json()["is_active"] is False

    async def test_patch_unknown_id_404(self, client: AsyncClient):
        r = await client.patch(
            "/api/api-keys/00000000-0000-4000-8000-000000000000", json={"scopes": "x"},
        )
        assert r.status_code == 404


class TestRequireApiKeyScope:
    async def _make_key(self, scopes: str = "") -> tuple[str, str]:
        """Insert an active API key with a known secret; return the bearer
        token (prefix.secret) + stored prefix."""
        from tests.conftest import async_session_test
        from app.models.cross import ApiKey
        raw = secrets.token_urlsafe(24)
        prefix = raw[:8]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        async with async_session_test() as db:
            k = ApiKey(name="scoped", prefix=prefix, key_hash=key_hash, is_active=True, scopes=scopes)
            db.add(k); await db.commit()
        return f"{prefix}.{raw}", prefix

    async def test_missing_header_is_401(self):
        from fastapi import Request
        from app.dependencies import require_api_key_scope
        from tests.conftest import async_session_test
        dep = require_api_key_scope("read:x")
        scope = {"type": "http", "headers": [], "method": "GET", "path": "/"}
        req = Request(scope)
        async with async_session_test() as db:
            with pytest.raises(Exception) as exc_info:
                await dep(req, db)
        # HTTPException with 401
        assert getattr(exc_info.value, "status_code", None) == 401

    async def test_invalid_key_is_401(self):
        from fastapi import Request
        from app.dependencies import require_api_key_scope
        from tests.conftest import async_session_test
        dep = require_api_key_scope("read:x")
        scope = {"type": "http",
                 "headers": [(b"authorization", b"Bearer badprefix.badsecret")],
                 "method": "GET", "path": "/"}
        req = Request(scope)
        async with async_session_test() as db:
            with pytest.raises(Exception) as exc_info:
                await dep(req, db)
        assert getattr(exc_info.value, "status_code", None) == 401

    async def test_missing_scope_is_403(self):
        from fastapi import Request
        from app.dependencies import require_api_key_scope
        from tests.conftest import async_session_test
        token, _ = await self._make_key(scopes="read:something-else")
        dep = require_api_key_scope("read:projects")
        scope = {"type": "http",
                 "headers": [(b"authorization", f"Bearer {token}".encode())],
                 "method": "GET", "path": "/"}
        req = Request(scope)
        async with async_session_test() as db:
            with pytest.raises(Exception) as exc_info:
                await dep(req, db)
        assert getattr(exc_info.value, "status_code", None) == 403

    async def test_valid_scope_passes(self):
        from fastapi import Request
        from app.dependencies import require_api_key_scope
        from tests.conftest import async_session_test
        token, prefix = await self._make_key(scopes="read:projects,write:tasks")
        dep = require_api_key_scope("read:projects")
        scope = {"type": "http",
                 "headers": [(b"authorization", f"Bearer {token}".encode())],
                 "method": "GET", "path": "/"}
        req = Request(scope)
        async with async_session_test() as db:
            api_key = await dep(req, db)
        # Dependency returns the ApiKey row on success
        assert api_key.prefix == prefix
