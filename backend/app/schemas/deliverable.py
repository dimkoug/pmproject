from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.deliverable import DeliverableStatus, QualityLevel


class DeliverableBase(BaseModel):
    name: str
    description: str | None = None
    status: DeliverableStatus = DeliverableStatus.PLANNED
    quality_level: QualityLevel = QualityLevel.NOT_ASSESSED
    acceptance_criteria: str | None = None
    completion_percentage: float = 0.0
    due_date: datetime | None = None


class DeliverableCreate(DeliverableBase):
    project_id: UUID


class DeliverableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: DeliverableStatus | None = None
    quality_level: QualityLevel | None = None
    acceptance_criteria: str | None = None
    completion_percentage: float | None = None
    due_date: datetime | None = None
    delivered_date: datetime | None = None


class DeliverableRead(DeliverableBase):
    id: UUID
    project_id: UUID
    delivered_date: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
