import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EngagementLevel(str, enum.Enum):
    UNAWARE = "unaware"
    RESISTANT = "resistant"
    NEUTRAL = "neutral"
    SUPPORTIVE = "supportive"
    LEADING = "leading"


class StakeholderCategory(str, enum.Enum):
    SPONSOR = "sponsor"
    CUSTOMER = "customer"
    END_USER = "end_user"
    REGULATOR = "regulator"
    SUPPLIER = "supplier"
    INTERNAL = "internal"
    EXTERNAL = "external"


class Stakeholder(Base):
    __tablename__ = "stakeholders"
    __table_args__ = (
        Index("ix_stakeholders_project_id", "project_id"),
        Index("ix_stakeholders_category", "project_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[StakeholderCategory] = mapped_column(
        Enum(StakeholderCategory), default=StakeholderCategory.INTERNAL
    )
    engagement_level: Mapped[EngagementLevel] = mapped_column(
        Enum(EngagementLevel), default=EngagementLevel.NEUTRAL
    )
    desired_engagement: Mapped[EngagementLevel] = mapped_column(
        Enum(EngagementLevel), default=EngagementLevel.SUPPORTIVE
    )
    influence: Mapped[str | None] = mapped_column(String(20), default="medium")
    interest: Mapped[str | None] = mapped_column(String(20), default="medium")
    expectations: Mapped[str | None] = mapped_column(Text)
    communication_needs: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="stakeholders", lazy="raise")
