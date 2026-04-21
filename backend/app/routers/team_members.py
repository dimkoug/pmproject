from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.team_member import TeamMember
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate
from app.websockets.manager import manager

router = APIRouter(prefix="/api/team-members", tags=["team"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[TeamMemberRead])
async def list_team_members(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamMember)
        .where(TeamMember.project_id == project_id)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=TeamMemberRead, status_code=201)
async def create_team_member(payload: TeamMemberCreate, db: AsyncSession = Depends(get_db)):
    member = TeamMember(**payload.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    await manager.broadcast(str(payload.project_id), "team_member_created", {"id": str(member.id), "name": member.name})
    return member


@router.get("/{member_id}", response_model=TeamMemberRead)
async def get_team_member(member_id: UUID, db: AsyncSession = Depends(get_db)):
    member = await db.get(TeamMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    return member


@router.patch("/{member_id}", response_model=TeamMemberRead)
async def update_team_member(member_id: UUID, payload: TeamMemberUpdate, db: AsyncSession = Depends(get_db)):
    member = await db.get(TeamMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    await db.commit()
    await db.refresh(member)
    await manager.broadcast(str(member.project_id), "team_member_updated", {"id": str(member.id)})
    return member


@router.delete("/{member_id}", status_code=204)
async def delete_team_member(member_id: UUID, db: AsyncSession = Depends(get_db)):
    member = await db.get(TeamMember, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    project_id = str(member.project_id)
    await db.delete(member)
    await db.commit()
    await manager.broadcast(project_id, "team_member_deleted", {"id": str(member_id)})
