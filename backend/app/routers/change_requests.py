from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.change_request import ChangeRequest
from app.schemas.change_request import ChangeRequestCreate, ChangeRequestRead, ChangeRequestUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/change-requests", tags=["change_requests"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[ChangeRequestRead])
async def list_change_requests(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.project_id == project_id)
        .order_by(ChangeRequest.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=ChangeRequestRead, status_code=201)
async def create_change_request(payload: ChangeRequestCreate, db: AsyncSession = Depends(get_db)):
    cr = ChangeRequest(**payload.model_dump())
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    await manager.broadcast(str(payload.project_id), "change_request_created", {"id": str(cr.id), "title": cr.title})
    return cr


@router.get("/{cr_id}", response_model=ChangeRequestRead)
async def get_change_request(cr_id: UUID, db: AsyncSession = Depends(get_db)):
    cr = await db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    return cr


@router.patch("/{cr_id}", response_model=ChangeRequestRead)
async def update_change_request(cr_id: UUID, payload: ChangeRequestUpdate, db: AsyncSession = Depends(get_db)):
    cr = await db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cr, key, value)
    await db.commit()
    await db.refresh(cr)
    await manager.broadcast(str(cr.project_id), "change_request_updated", {"id": str(cr.id), "status": cr.status.value})
    return cr


@router.delete("/{cr_id}", status_code=204)
async def delete_change_request(cr_id: UUID, db: AsyncSession = Depends(get_db)):
    cr = await db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    project_id = str(cr.project_id)
    await db.delete(cr)
    await db.commit()
    await manager.broadcast(project_id, "change_request_deleted", {"id": str(cr_id)})
