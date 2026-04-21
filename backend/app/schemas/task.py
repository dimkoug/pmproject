from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.task import TaskStatus, TaskPriority
from app.models.task_dependency import DependencyType


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    parent_id: UUID | None = None
    wbs_code: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    is_milestone: bool = False
    story_points: int | None = None
    duration_days: float | None = None
    optimistic_duration: float | None = None
    most_likely_duration: float | None = None
    pessimistic_duration: float | None = None
    planned_cost: float | None = None
    actual_cost: float | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    assignee_id: UUID | None = None


class TaskCreate(TaskBase):
    project_id: UUID


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    wbs_code: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    is_milestone: bool | None = None
    story_points: int | None = None
    duration_days: float | None = None
    optimistic_duration: float | None = None
    most_likely_duration: float | None = None
    pessimistic_duration: float | None = None
    planned_cost: float | None = None
    actual_cost: float | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    completed_date: datetime | None = None
    assignee_id: UUID | None = None


class TaskRead(TaskBase):
    id: UUID
    project_id: UUID
    completed_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DependencyCreate(BaseModel):
    project_id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: DependencyType = DependencyType.FS
    lag_days: float = 0.0


class DependencyRead(BaseModel):
    id: UUID
    project_id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: DependencyType
    lag_days: float

    class Config:
        from_attributes = True
