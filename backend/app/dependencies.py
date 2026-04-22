import hashlib
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cross import ApiKey
from app.models.user import User
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    try:
        uid = UUID(user_id)
    except ValueError:
        raise credentials_exception
    user = await db.get(User, uid)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


# ── API key auth (#9) ───────────────────────────────────────────────
# API keys are presented as `Authorization: Bearer <prefix>.<secret>` and stored
# as a SHA-256 hash of the secret. Scopes gate what each key can do.

async def _lookup_api_key(raw: str, db: AsyncSession) -> ApiKey | None:
    if "." not in raw:
        return None
    secret_part = raw.split(".", 1)[1]
    key_hash = hashlib.sha256(secret_part.encode()).hexdigest()
    row = (await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))).scalar_one_or_none()
    return row


def require_api_key_scope(*required: str):
    """FastAPI dependency factory. Requires ALL listed scopes to be present on
    the ApiKey. Use like:
        @router.get("/api/external/projects", dependencies=[Depends(require_api_key_scope("read:projects"))])
    """
    async def _dep(request: Request, db: AsyncSession = Depends(get_db)) -> ApiKey:
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing API key")
        raw = auth.split(" ", 1)[1].strip()
        key = await _lookup_api_key(raw, db)
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        have = {s for s in (key.scopes or "").split(",") if s}
        missing = [s for s in required if s not in have]
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing required scope(s): {', '.join(missing)}")
        # Best-effort last-used bookkeeping; swallow on failure so a replica race
        # never rejects an otherwise-valid request.
        try:
            key.last_used_at = datetime.utcnow()
            await db.commit()
        except Exception:
            await db.rollback()
        return key
    return _dep
