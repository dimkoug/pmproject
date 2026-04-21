import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskCategory(str, enum.Enum):
    TECHNICAL = "technical"
    EXTERNAL = "external"
    ORGANIZATIONAL = "organizational"
    PROJECT_MANAGEMENT = "project_management"


class RiskProbability(str, enum.Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskImpact(str, enum.Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    ANALYZING = "analyzing"
    PLANNED = "planned"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RiskStrategy(str, enum.Enum):
    AVOID = "avoid"
    MITIGATE = "mitigate"
    TRANSFER = "transfer"
    ACCEPT = "accept"
    ESCALATE = "escalate"
    EXPLOIT = "exploit"
    ENHANCE = "enhance"
    SHARE = "share"


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        Index("ix_risks_project_id", "project_id"),
        Index("ix_risks_project_created", "project_id", "created_at"),
        Index("ix_risks_project_status", "project_id", "status"),
        Index("ix_risks_owner_id", "owner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[RiskCategory] = mapped_column(
        Enum(RiskCategory), default=RiskCategory.TECHNICAL
    )
    probability: Mapped[RiskProbability] = mapped_column(
        Enum(RiskProbability), default=RiskProbability.MEDIUM
    )
    impact: Mapped[RiskImpact] = mapped_column(Enum(RiskImpact), default=RiskImpact.MEDIUM)
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus), default=RiskStatus.IDENTIFIED)
    strategy: Mapped[RiskStrategy] = mapped_column(Enum(RiskStrategy), default=RiskStrategy.MITIGATE)
    response_plan: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("team_members.id"))
    trigger_conditions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", back_populates="risks", lazy="raise")
    owner = relationship("TeamMember", foreign_keys=[owner_id], lazy="raise")
