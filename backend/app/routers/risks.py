from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.risk import Risk
from app.schemas.risk import RiskCreate, RiskRead, RiskUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/risks", tags=["risks"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[RiskRead])
async def list_risks(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Risk)
        .where(Risk.project_id == project_id)
        .order_by(Risk.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=RiskRead, status_code=201)
async def create_risk(payload: RiskCreate, db: AsyncSession = Depends(get_db)):
    risk = Risk(**payload.model_dump())
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    await manager.broadcast(str(payload.project_id), "risk_created", {"id": str(risk.id), "title": risk.title})
    return risk


@router.get("/{risk_id}", response_model=RiskRead)
async def get_risk(risk_id: UUID, db: AsyncSession = Depends(get_db)):
    risk = await db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@router.patch("/{risk_id}", response_model=RiskRead)
async def update_risk(risk_id: UUID, payload: RiskUpdate, db: AsyncSession = Depends(get_db)):
    risk = await db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(risk, key, value)
    await db.commit()
    await db.refresh(risk)
    await manager.broadcast(str(risk.project_id), "risk_updated", {"id": str(risk.id)})
    return risk


@router.delete("/{risk_id}", status_code=204)
async def delete_risk(risk_id: UUID, db: AsyncSession = Depends(get_db)):
    risk = await db.get(Risk, risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    project_id = str(risk.project_id)
    await db.delete(risk)
    await db.commit()
    await manager.broadcast(project_id, "risk_deleted", {"id": str(risk_id)})
