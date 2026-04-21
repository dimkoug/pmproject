from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.change_request import ChangeStatus, ChangeImpact


class ChangeRequestBase(BaseModel):
    title: str
    description: str | None = None
    justification: str | None = None
    status: ChangeStatus = ChangeStatus.SUBMITTED
    impact: ChangeImpact = ChangeImpact.MEDIUM
    impact_analysis: str | None = None
    requested_by_id: UUID | None = None
    reviewed_by_id: UUID | None = None


class ChangeRequestCreate(ChangeRequestBase):
    project_id: UUID


class ChangeRequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    justification: str | None = None
    status: ChangeStatus | None = None
    impact: ChangeImpact | None = None
    impact_analysis: str | None = None
    requested_by_id: UUID | None = None
    reviewed_by_id: UUID | None = None


class ChangeRequestRead(ChangeRequestBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
