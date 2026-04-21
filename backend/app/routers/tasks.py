from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[TaskRead])
async def list_tasks(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=TaskRead, status_code=201, dependencies=[Depends(require_permission("projects.task.create"))])
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await manager.broadcast(str(payload.project_id), "task_created", {"id": str(task.id), "title": task.title})
    return task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead, dependencies=[Depends(require_permission("projects.task.update"))])
async def update_task(task_id: UUID, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    await manager.broadcast(
        str(task.project_id), "task_updated",
        {"id": str(task.id), "title": task.title, "status": task.status.value},
    )
    return task


@router.delete("/{task_id}", status_code=204, dependencies=[Depends(require_permission("projects.task.delete"))])
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project_id = str(task.project_id)
    await db.delete(task)
    await db.commit()
    await manager.broadcast(project_id, "task_deleted", {"id": str(task_id)})
