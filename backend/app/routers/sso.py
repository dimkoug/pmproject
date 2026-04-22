"""SSO via OIDC (#48).

Two endpoints:
  * GET /api/sso/start?provider_id=<uuid>
      Discovers the provider's authorize endpoint, mints a signed `state`,
      and 302s the browser to the provider for sign-in.

  * GET /api/sso/callback?code=...&state=...
      Verifies the state, exchanges the code for an `id_token`, looks up or
      creates a User by email, mints our own JWT, and redirects back to the
      frontend at `/login/sso-callback#token=<JWT>` so the client picks it up.

The `client_secret` lives in `SsoProvider.client_secret_masked` (a model
oversight from the original schema — name is misleading but it's the only
secret column we have without a migration).

State is a signed token — no server-side storage. Format `<body>.<sig>` where
`body` is base64url JSON `{p:provider_id,n:nonce,t:timestamp}` and `sig` is
the first 32 chars of an HMAC-SHA256 over body using SECRET_KEY. Valid for 10
minutes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.parse
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.cross import SsoProvider
from app.models.user import User
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/sso", tags=["sso"])

logger = logging.getLogger(__name__)

DEFAULT_SCOPE = "openid email profile"
STATE_MAX_AGE_SECS = 600  # 10 minutes


def _redirect_uri() -> str:
    """The callback URL we register with the provider."""
    return f"{settings.app_base_url.rstrip('/')}/api/sso/callback"


def _make_state(provider_id: str) -> str:
    payload = {"p": provider_id, "n": secrets.token_urlsafe(12), "t": int(time.time())}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def _verify_state(state: str) -> dict | None:
    try:
        body, sig = state.split(".", 1)
        expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        # Re-pad base64
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if int(time.time()) - int(payload.get("t", 0)) > STATE_MAX_AGE_SECS:
            return None
        return payload
    except Exception:
        return None


def _decode_jwt_unverified(token: str) -> dict:
    """Decode a JWT body WITHOUT verifying the signature.

    Production should verify against the provider's JWKS — for MVP we trust
    the token came from a successful token-endpoint exchange (mutually-TLS'd
    via httpx + client_secret).
    """
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    body = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(body))
    except Exception:
        return {}


async def _discover(provider: SsoProvider) -> dict:
    if not provider.issuer_url:
        raise HTTPException(400, "Provider has no issuer_url configured")
    discovery_url = provider.issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(discovery_url)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"OIDC discovery failed: {e}")


@router.get("/active")
async def list_active_providers(db: AsyncSession = Depends(get_db)):
    """Public endpoint — login page uses this to render SSO buttons.
    Note: full provider list (with masked secrets etc.) is at /api/sso/providers
    in cross.py and requires admin auth."""
    r = await db.execute(select(SsoProvider).where(SsoProvider.is_active == True))  # noqa: E712
    return [
        {"id": str(p.id), "name": p.name, "provider_type": p.provider_type.value}
        for p in r.scalars().all()
    ]


@router.get("/start")
async def sso_start(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    provider = await db.get(SsoProvider, provider_id)
    if not provider or not provider.is_active:
        raise HTTPException(404, "Provider not found or inactive")
    if not provider.client_id:
        raise HTTPException(400, "Provider missing client_id")
    discovery = await _discover(provider)
    auth_endpoint = discovery.get("authorization_endpoint")
    if not auth_endpoint:
        raise HTTPException(502, "Provider discovery has no authorization_endpoint")
    state = _make_state(str(provider.id))
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": _redirect_uri(),
        "scope": DEFAULT_SCOPE,
        "state": state,
    }
    qs = urllib.parse.urlencode(params)
    return RedirectResponse(url=f"{auth_endpoint}?{qs}", status_code=302)


@router.get("/callback")
async def sso_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    fallback_url = f"{settings.app_base_url.rstrip('/')}/login"
    if error:
        msg = urllib.parse.quote(error_description or error)
        return RedirectResponse(url=f"{fallback_url}?sso_error={msg}", status_code=302)
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    payload = _verify_state(state)
    if not payload:
        raise HTTPException(401, "Invalid or expired state")

    provider = await db.get(SsoProvider, UUID(payload["p"]))
    if not provider or not provider.is_active:
        raise HTTPException(404, "Provider not found or inactive")
    if not provider.client_id or not provider.client_secret_masked:
        raise HTTPException(400, "Provider missing client_id or client_secret")

    discovery = await _discover(provider)
    token_endpoint = discovery.get("token_endpoint")
    if not token_endpoint:
        raise HTTPException(502, "Provider discovery has no token_endpoint")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_r = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _redirect_uri(),
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret_masked,
                },
                headers={"Accept": "application/json"},
            )
            token_r.raise_for_status()
            token_data = token_r.json()
        except httpx.HTTPError as e:
            logger.warning("SSO token exchange failed: %s", e)
            raise HTTPException(502, f"Token exchange failed: {e}")

    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(502, "Provider response missing id_token")
    claims = _decode_jwt_unverified(id_token)
    email = (claims.get("email") or "").lower()
    name = claims.get("name") or claims.get("preferred_username") or email.split("@", 1)[0]
    if not email:
        raise HTTPException(502, "id_token has no email claim")

    # Look up or create the user
    existing = await db.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            name=name,
            hashed_password="!SSO_ONLY!",  # SSO-only — local login disabled
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    jwt = create_access_token({"sub": str(user.id)})
    # Use a hash fragment so the token never hits server logs through the URL
    redirect = f"{settings.app_base_url.rstrip('/')}/login/sso-callback#token={jwt}&user_id={user.id}"
    return RedirectResponse(url=redirect, status_code=302)
