from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.stakeholder import Stakeholder
from app.schemas.stakeholder import StakeholderCreate, StakeholderRead, StakeholderUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/stakeholders", tags=["stakeholders"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[StakeholderRead])
async def list_stakeholders(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Stakeholder)
        .where(Stakeholder.project_id == project_id)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=StakeholderRead, status_code=201)
async def create_stakeholder(payload: StakeholderCreate, db: AsyncSession = Depends(get_db)):
    stakeholder = Stakeholder(**payload.model_dump())
    db.add(stakeholder)
    await db.commit()
    await db.refresh(stakeholder)
    await manager.broadcast(str(payload.project_id), "stakeholder_created", {"id": str(stakeholder.id), "name": stakeholder.name})
    return stakeholder


@router.get("/{stakeholder_id}", response_model=StakeholderRead)
async def get_stakeholder(stakeholder_id: UUID, db: AsyncSession = Depends(get_db)):
    stakeholder = await db.get(Stakeholder, stakeholder_id)
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    return stakeholder


@router.patch("/{stakeholder_id}", response_model=StakeholderRead)
async def update_stakeholder(stakeholder_id: UUID, payload: StakeholderUpdate, db: AsyncSession = Depends(get_db)):
    stakeholder = await db.get(Stakeholder, stakeholder_id)
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(stakeholder, key, value)
    await db.commit()
    await db.refresh(stakeholder)
    await manager.broadcast(str(stakeholder.project_id), "stakeholder_updated", {"id": str(stakeholder.id)})
    return stakeholder


@router.delete("/{stakeholder_id}", status_code=204)
async def delete_stakeholder(stakeholder_id: UUID, db: AsyncSession = Depends(get_db)):
    stakeholder = await db.get(Stakeholder, stakeholder_id)
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    project_id = str(stakeholder.project_id)
    await db.delete(stakeholder)
    await db.commit()
    await manager.broadcast(project_id, "stakeholder_deleted", {"id": str(stakeholder_id)})
