from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserRead(BaseModel):
    id: UUID
    email: str
    name: str
    role: str = "member"
    is_active: bool
    timezone: str = "UTC"
    language: str = "en"
    phone: str | None = None
    notify_email: bool = True
    notify_sms: bool = False
    is_totp_enabled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    timezone: str | None = None
    language: str | None = None
    phone: str | None = None
    notify_email: bool | None = None
    notify_sms: bool | None = None
