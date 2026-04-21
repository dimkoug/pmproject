from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementCreate, MeasurementRead, MeasurementUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/measurements", tags=["measurements"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[MeasurementRead])
async def list_measurements(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Measurement)
        .where(Measurement.project_id == project_id)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=MeasurementRead, status_code=201)
async def create_measurement(payload: MeasurementCreate, db: AsyncSession = Depends(get_db)):
    measurement = Measurement(**payload.model_dump())
    db.add(measurement)
    await db.commit()
    await db.refresh(measurement)
    await manager.broadcast(str(payload.project_id), "measurement_created", {"id": str(measurement.id), "name": measurement.name})
    return measurement


@router.get("/{measurement_id}", response_model=MeasurementRead)
async def get_measurement(measurement_id: UUID, db: AsyncSession = Depends(get_db)):
    measurement = await db.get(Measurement, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return measurement


@router.patch("/{measurement_id}", response_model=MeasurementRead)
async def update_measurement(measurement_id: UUID, payload: MeasurementUpdate, db: AsyncSession = Depends(get_db)):
    measurement = await db.get(Measurement, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(measurement, key, value)
    await db.commit()
    await db.refresh(measurement)
    await manager.broadcast(str(measurement.project_id), "measurement_updated", {"id": str(measurement.id)})
    return measurement


@router.delete("/{measurement_id}", status_code=204)
async def delete_measurement(measurement_id: UUID, db: AsyncSession = Depends(get_db)):
    measurement = await db.get(Measurement, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    project_id = str(measurement.project_id)
    await db.delete(measurement)
    await db.commit()
    await manager.broadcast(project_id, "measurement_deleted", {"id": str(measurement_id)})
