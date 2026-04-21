from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.stakeholder import EngagementLevel, StakeholderCategory


class StakeholderBase(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    category: StakeholderCategory = StakeholderCategory.INTERNAL
    engagement_level: EngagementLevel = EngagementLevel.NEUTRAL
    desired_engagement: EngagementLevel = EngagementLevel.SUPPORTIVE
    influence: str | None = "medium"
    interest: str | None = "medium"
    expectations: str | None = None
    communication_needs: str | None = None


class StakeholderCreate(StakeholderBase):
    project_id: UUID


class StakeholderUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    category: StakeholderCategory | None = None
    engagement_level: EngagementLevel | None = None
    desired_engagement: EngagementLevel | None = None
    influence: str | None = None
    interest: str | None = None
    expectations: str | None = None
    communication_needs: str | None = None


class StakeholderRead(StakeholderBase):
    id: UUID
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
