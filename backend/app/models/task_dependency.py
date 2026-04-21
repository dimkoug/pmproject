import uuid
import enum

from sqlalchemy import Enum, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DependencyType(str, enum.Enum):
    FS = "finish_to_start"
    FF = "finish_to_finish"
    SS = "start_to_start"
    SF = "start_to_finish"


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("predecessor_id", "successor_id", name="uq_task_dependency"),
        Index("ix_task_deps_predecessor", "predecessor_id"),
        Index("ix_task_deps_successor", "successor_id"),
        Index("ix_task_deps_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    predecessor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    successor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType), default=DependencyType.FS
    )
    lag_days: Mapped[float] = mapped_column(Float, default=0.0)
