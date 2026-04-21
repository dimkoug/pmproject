from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.team_member import TeamRole


class TeamMemberBase(BaseModel):
    name: str
    email: str | None = None
    role: TeamRole = TeamRole.DEVELOPER
    responsibilities: str | None = None
    skills: str | None = None
    availability: float | None = 100.0


class TeamMemberCreate(TeamMemberBase):
    project_id: UUID


class TeamMemberUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: TeamRole | None = None
    responsibilities: str | None = None
    skills: str | None = None
    availability: float | None = None


class TeamMemberRead(TeamMemberBase):
    id: UUID
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
