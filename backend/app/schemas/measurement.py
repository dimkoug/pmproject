from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.measurement import MetricType, MeasurementDomain


class MeasurementBase(BaseModel):
    name: str
    description: str | None = None
    metric_type: MetricType = MetricType.KPI
    domain: MeasurementDomain = MeasurementDomain.VALUE
    target_value: float | None = None
    actual_value: float | None = None
    unit: str | None = None
    threshold_red: float | None = None
    threshold_yellow: float | None = None
    threshold_green: float | None = None
    measured_at: datetime | None = None


class MeasurementCreate(MeasurementBase):
    project_id: UUID


class MeasurementUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    metric_type: MetricType | None = None
    domain: MeasurementDomain | None = None
    target_value: float | None = None
    actual_value: float | None = None
    unit: str | None = None
    threshold_red: float | None = None
    threshold_yellow: float | None = None
    threshold_green: float | None = None
    measured_at: datetime | None = None


class MeasurementRead(MeasurementBase):
    id: UUID
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
