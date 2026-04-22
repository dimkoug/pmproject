from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.workspaces import get_active_workspace_id
from app.websockets.manager import manager

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    request: Request,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Project).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc()).offset(skip).limit(limit)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Project.workspace_id == ws_id) | (Project.workspace_id.is_(None)))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=ProjectRead, status_code=201, dependencies=[Depends(require_permission("projects.project.create"))])
async def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        from app.services.plans import check_can_add_project
        await check_can_add_project(db, ws_id)
    project = Project(**payload.model_dump(), workspace_id=ws_id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    await manager.broadcast_all("project_created", {"id": str(project.id), "name": project.name})
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead, dependencies=[Depends(require_permission("projects.project.update"))])
async def update_project(project_id: UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    await manager.broadcast(str(project_id), "project_updated", {"id": str(project.id), "name": project.name})
    return project


@router.delete("/{project_id}", status_code=204, dependencies=[Depends(require_permission("projects.project.delete"))])
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete: sets `deleted_at` rather than removing the row. Visible
    in /admin/trash for 30 days; purge or restore from there."""
    from datetime import datetime, timezone
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast_all("project_deleted", {"id": str(project_id)})
