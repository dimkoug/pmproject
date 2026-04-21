from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.risk import RiskCategory, RiskProbability, RiskImpact, RiskStatus, RiskStrategy


class RiskBase(BaseModel):
    title: str
    description: str | None = None
    category: RiskCategory = RiskCategory.TECHNICAL
    probability: RiskProbability = RiskProbability.MEDIUM
    impact: RiskImpact = RiskImpact.MEDIUM
    status: RiskStatus = RiskStatus.IDENTIFIED
    strategy: RiskStrategy = RiskStrategy.MITIGATE
    response_plan: str | None = None
    owner_id: UUID | None = None
    trigger_conditions: str | None = None


class RiskCreate(RiskBase):
    project_id: UUID


class RiskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: RiskCategory | None = None
    probability: RiskProbability | None = None
    impact: RiskImpact | None = None
    status: RiskStatus | None = None
    strategy: RiskStrategy | None = None
    response_plan: str | None = None
    owner_id: UUID | None = None
    trigger_conditions: str | None = None


class RiskRead(RiskBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
