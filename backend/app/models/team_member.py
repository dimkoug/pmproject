import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamRole(str, enum.Enum):
    PROJECT_MANAGER = "project_manager"
    SCRUM_MASTER = "scrum_master"
    PRODUCT_OWNER = "product_owner"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    TESTER = "tester"
    DESIGNER = "designer"
    ARCHITECT = "architect"
    OTHER = "other"


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        Index("ix_team_members_project_id", "project_id"),
        Index("ix_team_members_project_role", "project_id", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), default=TeamRole.DEVELOPER)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)
    availability: Mapped[float | None] = mapped_column(default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="team_members", lazy="raise")
