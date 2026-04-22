from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserRead, UserSettingsUpdate
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.is_totp_enabled:
        if not payload.totp_code:
            # 401 with explicit detail so the client knows to prompt for the code
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="TOTP_REQUIRED",
            )
        import pyotp
        totp = pyotp.TOTP(user.totp_secret or "")
        if not totp.verify(payload.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/settings", response_model=UserRead)
async def update_me_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.timezone is not None:
        # Best-effort validate — reject anything that isn't a recognised IANA zone.
        # We do a quick zoneinfo lookup; users can only set zones Python knows.
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(payload.timezone)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Unknown timezone: {payload.timezone}")
        current_user.timezone = payload.timezone
    if payload.language is not None:
        if not payload.language or len(payload.language) > 10:
            raise HTTPException(status_code=400, detail="Invalid language code")
        current_user.language = payload.language
    if payload.phone is not None:
        current_user.phone = payload.phone or None
    if payload.notify_email is not None:
        current_user.notify_email = payload.notify_email
    if payload.notify_sms is not None:
        current_user.notify_sms = payload.notify_sms
    await db.commit()
    await db.refresh(current_user)
    return current_user


# ── Forgot-password / reset flow (#1) ─────────────────────────────────

from pydantic import BaseModel as _BM
import hashlib as _hashlib
import secrets as _secrets
from datetime import timedelta as _td, timezone


class ForgotPasswordIn(_BM):
    email: str


class ResetPasswordIn(_BM):
    token: str
    new_password: str


def _hash_token(raw: str) -> str:
    return _hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, db: AsyncSession = Depends(get_db)):
    """Issue a reset token for `email` if it exists.
    Returns 200 regardless of whether the email is on file — we don't want to
    leak account existence. If a user matched, we generate a token, stash its
    hash (plus 1-hour expiry), and queue an email with the reset link."""
    from app.models.password_reset import PasswordResetToken
    from app.services.email import send_email_task
    from app.config import settings as _settings
    import logging as _logging
    _log = _logging.getLogger("app.auth")

    from datetime import datetime
    result = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        raw = _secrets.token_urlsafe(32)
        token_hash = _hash_token(raw)
        expires = datetime.now(timezone.utc) + _td(hours=1)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
        await db.commit()
        reset_url = f"{_settings.app_base_url.rstrip('/')}/reset-password#token={raw}"
        try:
            send_email_task.delay(
                user.email,
                "Reset your password",
                f"Click the link to reset your password (valid 1 hour):\n\n{reset_url}\n\nIf you didn't request this, ignore this email.",
                f"<p>Click the link below to reset your password (valid 1 hour):</p>"
                f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
                f"<p>If you didn't request this, ignore this email.</p>",
            )
        except Exception:
            _log.exception("Failed to queue reset email for %s", user.email)
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)):
    from app.models.password_reset import PasswordResetToken
    from datetime import datetime
    token_hash = _hash_token(payload.token)
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(400, "Invalid or expired token")
    if row.used_at is not None:
        raise HTTPException(400, "This reset link has already been used")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "This reset link has expired")
    if len(payload.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Account not available")
    user.hashed_password = hash_password(payload.new_password)
    row.used_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


# ── TOTP / 2FA (#45) ──────────────────────────────────────────────────

from pydantic import BaseModel


class TotpEnrollOut(BaseModel):
    secret: str
    provisioning_uri: str


class TotpConfirmIn(BaseModel):
    code: str


class TotpDisableIn(BaseModel):
    password: str
    code: str


@router.post("/totp/enroll", response_model=TotpEnrollOut)
async def totp_enroll(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a fresh TOTP secret. Stored unconfirmed until /totp/confirm
    succeeds — calling enroll again invalidates the previous secret."""
    if current_user.is_totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP already enabled — disable it first to re-enrol")
    import pyotp
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    await db.commit()
    issuer = "PM Project"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name=issuer)
    return TotpEnrollOut(secret=secret, provisioning_uri=uri)


@router.post("/totp/confirm", response_model=UserRead)
async def totp_confirm(payload: TotpConfirmIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.is_totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP already enabled")
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="No pending enrolment — call /totp/enroll first")
    import pyotp
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code — try again with the current 6-digit value")
    current_user.is_totp_enabled = True
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/totp/disable", response_model=UserRead)
async def totp_disable(payload: TotpDisableIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_totp_enabled:
        raise HTTPException(status_code=400, detail="TOTP not enabled")
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong password")
    import pyotp
    totp = pyotp.TOTP(current_user.totp_secret or "")
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    current_user.is_totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    await db.refresh(current_user)
    return current_user
