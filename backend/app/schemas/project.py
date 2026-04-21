from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.project import DevelopmentApproach, ProjectStatus, DeliveryCadence


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    status: ProjectStatus = ProjectStatus.INITIATING
    development_approach: DevelopmentApproach = DevelopmentApproach.PREDICTIVE
    delivery_cadence: DeliveryCadence = DeliveryCadence.SINGLE
    start_date: datetime | None = None
    end_date: datetime | None = None
    budget: float | None = 0.0
    vision: str | None = None
    objectives: str | None = None
    success_criteria: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    development_approach: DevelopmentApproach | None = None
    delivery_cadence: DeliveryCadence | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    budget: float | None = None
    vision: str | None = None
    objectives: str | None = None
    success_criteria: str | None = None


class ProjectRead(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
