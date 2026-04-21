from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.cache import cache_get, cache_set
from app.config import settings
from app.models.task import Task
from app.models.risk import Risk
from app.models.deliverable import Deliverable
from app.models.stakeholder import Stakeholder
from app.models.team_member import TeamMember
from app.models.change_request import ChangeRequest
from app.models.measurement import Measurement

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/{project_id}")
async def get_dashboard(project_id: UUID, db: AsyncSession = Depends(get_db)):
    # Check Redis cache first
    cache_key = f"dashboard:{project_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    # Query 1: All status distributions + counts in a single UNION ALL
    # Each sub-query returns (entity, key, count) rows
    counts_query = union_all(
        select(
            literal("task").label("entity"),
            cast(Task.status, String).label("key"),
            func.count(Task.id).label("cnt"),
        ).where(Task.project_id == project_id).group_by(Task.status),
        select(
            literal("risk").label("entity"),
            cast(Risk.status, String).label("key"),
            func.count(Risk.id).label("cnt"),
        ).where(Risk.project_id == project_id).group_by(Risk.status),
        select(
            literal("deliverable").label("entity"),
            cast(Deliverable.status, String).label("key"),
            func.count(Deliverable.id).label("cnt"),
        ).where(Deliverable.project_id == project_id).group_by(Deliverable.status),
        select(
            literal("stakeholder").label("entity"),
            literal("total").label("key"),
            func.count(Stakeholder.id).label("cnt"),
        ).where(Stakeholder.project_id == project_id),
        select(
            literal("team").label("entity"),
            literal("total").label("key"),
            func.count(TeamMember.id).label("cnt"),
        ).where(TeamMember.project_id == project_id),
        select(
            literal("change_request").label("entity"),
            literal("total").label("key"),
            func.count(ChangeRequest.id).label("cnt"),
        ).where(ChangeRequest.project_id == project_id),
    )

    result = await db.execute(counts_query)
    rows = result.all()

    task_stats: dict[str, int] = {}
    risk_stats: dict[str, int] = {}
    deliverable_stats: dict[str, int] = {}
    stakeholder_count = 0
    team_count = 0
    cr_count = 0

    for entity, key, cnt in rows:
        k = key.lower() if key else key
        if entity == "task":
            task_stats[k] = cnt
        elif entity == "risk":
            risk_stats[k] = cnt
        elif entity == "deliverable":
            deliverable_stats[k] = cnt
        elif entity == "stakeholder":
            stakeholder_count = cnt
        elif entity == "team":
            team_count = cnt
        elif entity == "change_request":
            cr_count = cnt

    # Query 2: Latest measurements (only query that needs actual rows)
    meas_result = await db.execute(
        select(
            Measurement.id,
            Measurement.name,
            Measurement.domain,
            Measurement.target_value,
            Measurement.actual_value,
            Measurement.unit,
        )
        .where(Measurement.project_id == project_id)
        .order_by(Measurement.created_at.desc())
        .limit(10)
    )
    measurements = [
        {
            "id": str(row.id),
            "name": row.name,
            "domain": row.domain.value,
            "target_value": row.target_value,
            "actual_value": row.actual_value,
            "unit": row.unit,
        }
        for row in meas_result.all()
    ]

    response = {
        "task_stats": task_stats,
        "risk_stats": risk_stats,
        "deliverable_stats": deliverable_stats,
        "stakeholder_count": stakeholder_count,
        "team_count": team_count,
        "change_request_count": cr_count,
        "measurements": measurements,
    }
    await cache_set(cache_key, response, ttl=settings.cache_ttl_dashboard)
    return response
