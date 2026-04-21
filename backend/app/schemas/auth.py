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
    created_at: datetime

    class Config:
        from_attributes = True
