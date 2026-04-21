import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LessonCategory(str, enum.Enum):
    PROCESS = "process"
    TECHNICAL = "technical"
    TEAM = "team"
    COMMUNICATION = "communication"
    RISK = "risk"
    STAKEHOLDER = "stakeholder"
    OTHER = "other"


class LessonLearned(Base):
    __tablename__ = "lessons_learned"
    __table_args__ = (
        Index("ix_lessons_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[LessonCategory] = mapped_column(Enum(LessonCategory), default=LessonCategory.OTHER)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
