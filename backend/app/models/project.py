import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class DevelopmentApproach(str, enum.Enum):
    PREDICTIVE = "predictive"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"
    AGILE = "agile"


class ProjectStatus(str, enum.Enum):
    INITIATING = "initiating"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    CLOSING = "closing"
    CLOSED = "closed"


class DeliveryCadence(str, enum.Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    PERIODIC = "periodic"


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_created_at", "created_at"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Soft delete: when set, the row is treated as trashed and filtered out
    # of every list endpoint. Restorable via /admin/trash.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.INITIATING
    )
    development_approach: Mapped[DevelopmentApproach] = mapped_column(
        Enum(DevelopmentApproach), default=DevelopmentApproach.PREDICTIVE
    )
    delivery_cadence: Mapped[DeliveryCadence] = mapped_column(
        Enum(DeliveryCadence), default=DeliveryCadence.SINGLE
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget: Mapped[float | None] = mapped_column(default=0.0)
    vision: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[str | None] = mapped_column(Text)
    success_criteria: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    stakeholders = relationship("Stakeholder", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    team_members = relationship("TeamMember", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    deliverables = relationship("Deliverable", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    measurements = relationship("Measurement", back_populates="project", cascade="all, delete-orphan", lazy="raise")
    change_requests = relationship("ChangeRequest", back_populates="project", cascade="all, delete-orphan", lazy="raise")
