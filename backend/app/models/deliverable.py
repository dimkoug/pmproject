import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliverableStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class QualityLevel(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    BELOW_STANDARD = "below_standard"
    MEETS_STANDARD = "meets_standard"
    EXCEEDS_STANDARD = "exceeds_standard"


class Deliverable(Base):
    __tablename__ = "deliverables"
    __table_args__ = (
        Index("ix_deliverables_project_id", "project_id"),
        Index("ix_deliverables_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DeliverableStatus] = mapped_column(
        Enum(DeliverableStatus), default=DeliverableStatus.PLANNED
    )
    quality_level: Mapped[QualityLevel] = mapped_column(
        Enum(QualityLevel), default=QualityLevel.NOT_ASSESSED
    )
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="deliverables", lazy="raise")
