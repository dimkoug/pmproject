from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.deliverable import Deliverable
from app.schemas.deliverable import DeliverableCreate, DeliverableRead, DeliverableUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/deliverables", tags=["deliverables"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[DeliverableRead])
async def list_deliverables(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Deliverable)
        .where(Deliverable.project_id == project_id)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=DeliverableRead, status_code=201, dependencies=[Depends(require_permission("projects.deliverable.manage"))])
async def create_deliverable(payload: DeliverableCreate, db: AsyncSession = Depends(get_db)):
    deliverable = Deliverable(**payload.model_dump())
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)
    await manager.broadcast(str(payload.project_id), "deliverable_created", {"id": str(deliverable.id), "name": deliverable.name})
    return deliverable


@router.get("/{deliverable_id}", response_model=DeliverableRead)
async def get_deliverable(deliverable_id: UUID, db: AsyncSession = Depends(get_db)):
    deliverable = await db.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return deliverable


@router.patch("/{deliverable_id}", response_model=DeliverableRead, dependencies=[Depends(require_permission("projects.deliverable.manage"))])
async def update_deliverable(deliverable_id: UUID, payload: DeliverableUpdate, db: AsyncSession = Depends(get_db)):
    deliverable = await db.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(deliverable, key, value)
    await db.commit()
    await db.refresh(deliverable)
    await manager.broadcast(str(deliverable.project_id), "deliverable_updated", {"id": str(deliverable.id)})
    return deliverable


@router.delete("/{deliverable_id}", status_code=204, dependencies=[Depends(require_permission("projects.deliverable.manage"))])
async def delete_deliverable(deliverable_id: UUID, db: AsyncSession = Depends(get_db)):
    deliverable = await db.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    project_id = str(deliverable.project_id)
    await db.delete(deliverable)
    await db.commit()
    await manager.broadcast(project_id, "deliverable_deleted", {"id": str(deliverable_id)})
