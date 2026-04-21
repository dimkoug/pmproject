import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetricType(str, enum.Enum):
    KPI = "kpi"
    LEADING = "leading"
    LAGGING = "lagging"
    OUTCOME = "outcome"


class MeasurementDomain(str, enum.Enum):
    SCHEDULE = "schedule"
    COST = "cost"
    QUALITY = "quality"
    SCOPE = "scope"
    RISK = "risk"
    STAKEHOLDER = "stakeholder"
    TEAM = "team"
    VALUE = "value"


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        Index("ix_measurements_project_id", "project_id"),
        Index("ix_measurements_project_created", "project_id", "created_at"),
        Index("ix_measurements_domain", "project_id", "domain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metric_type: Mapped[MetricType] = mapped_column(Enum(MetricType), default=MetricType.KPI)
    domain: Mapped[MeasurementDomain] = mapped_column(
        Enum(MeasurementDomain), default=MeasurementDomain.VALUE
    )
    target_value: Mapped[float | None] = mapped_column(Float)
    actual_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    threshold_red: Mapped[float | None] = mapped_column(Float)
    threshold_yellow: Mapped[float | None] = mapped_column(Float)
    threshold_green: Mapped[float | None] = mapped_column(Float)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="measurements", lazy="raise")
