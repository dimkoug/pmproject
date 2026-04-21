from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.task import Task
from app.models.risk import Risk
from app.models.deliverable import Deliverable
from app.models.stakeholder import Stakeholder
from app.models.team_member import TeamMember
from app.models.change_request import ChangeRequest
from app.models.measurement import Measurement
from app.models.task_dependency import TaskDependency
from app.services.schedule import TaskNode, Dependency, compute_cpm, compute_pert

router = APIRouter(prefix="/api/projects", tags=["reports"], dependencies=[Depends(get_current_user)])


# ── Project Summary Report ──────────────────────────────────────────

@router.get("/{project_id}/reports/summary")
async def report_summary(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Task stats
    task_rows = (await db.execute(
        select(cast(Task.status, String), func.count(Task.id))
        .where(Task.project_id == project_id).group_by(Task.status)
    )).all()
    task_stats = {r[0].lower(): r[1] for r in task_rows}
    total_tasks = sum(task_stats.values())
    done_tasks = task_stats.get("done", 0)

    # Risk stats
    risk_rows = (await db.execute(
        select(cast(Risk.status, String), func.count(Risk.id))
        .where(Risk.project_id == project_id).group_by(Risk.status)
    )).all()
    risk_stats = {r[0].lower(): r[1] for r in risk_rows}
    open_risks = sum(v for k, v in risk_stats.items() if k not in ("resolved", "closed"))

    # High-impact risks
    high_risks = (await db.execute(
        select(Risk.title, cast(Risk.probability, String), cast(Risk.impact, String), cast(Risk.status, String))
        .where(Risk.project_id == project_id)
        .where(Risk.impact.in_(["HIGH", "VERY_HIGH"]))
        .where(Risk.status.notin_(["RESOLVED", "CLOSED"]))
    )).all()

    # Deliverable stats
    del_rows = (await db.execute(
        select(cast(Deliverable.status, String), func.count(Deliverable.id))
        .where(Deliverable.project_id == project_id).group_by(Deliverable.status)
    )).all()
    del_stats = {r[0].lower(): r[1] for r in del_rows}
    total_deliverables = sum(del_stats.values())
    accepted_deliverables = del_stats.get("accepted", 0)

    # Counts
    stakeholder_count = await db.scalar(
        select(func.count(Stakeholder.id)).where(Stakeholder.project_id == project_id)
    ) or 0
    team_count = await db.scalar(
        select(func.count(TeamMember.id)).where(TeamMember.project_id == project_id)
    ) or 0
    cr_count = await db.scalar(
        select(func.count(ChangeRequest.id)).where(ChangeRequest.project_id == project_id)
    ) or 0
    pending_crs = await db.scalar(
        select(func.count(ChangeRequest.id))
        .where(ChangeRequest.project_id == project_id)
        .where(ChangeRequest.status.in_(["SUBMITTED", "UNDER_REVIEW"]))
    ) or 0

    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "status": project.status.value,
            "development_approach": project.development_approach.value,
            "budget": project.budget,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
        },
        "tasks": {
            "total": total_tasks,
            "done": done_tasks,
            "completion_pct": round(done_tasks / total_tasks * 100, 1) if total_tasks else 0,
            "by_status": task_stats,
        },
        "risks": {
            "total": sum(risk_stats.values()),
            "open": open_risks,
            "by_status": risk_stats,
            "high_impact": [
                {"title": r[0], "probability": r[1].lower(), "impact": r[2].lower(), "status": r[3].lower()}
                for r in high_risks
            ],
        },
        "deliverables": {
            "total": total_deliverables,
            "accepted": accepted_deliverables,
            "acceptance_pct": round(accepted_deliverables / total_deliverables * 100, 1) if total_deliverables else 0,
            "by_status": del_stats,
        },
        "stakeholders": {"count": stakeholder_count},
        "team": {"count": team_count},
        "change_requests": {"total": cr_count, "pending": pending_crs},
    }


# ── Schedule Report (CPM + PERT) ────────────────────────────────────

@router.get("/{project_id}/reports/schedule")
async def report_schedule(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load network
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()

    nodes = [
        TaskNode(
            id=str(t.id), title=t.title, duration=t.duration_days or 0,
            optimistic=t.optimistic_duration, most_likely=t.most_likely_duration,
            pessimistic=t.pessimistic_duration, status=t.status.value,
        )
        for t in tasks
    ]
    edges = [
        Dependency(
            predecessor_id=str(d.predecessor_id), successor_id=str(d.successor_id),
            dep_type=d.dependency_type.value, lag=d.lag_days,
        )
        for d in deps
    ]

    cpm = compute_cpm(nodes, edges)

    # PERT with auto-generated targets
    targets = []
    if cpm.project_duration > 0:
        d = cpm.project_duration
        targets = [round(d * 0.8, 1), round(d * 0.9, 1), round(d, 1), round(d * 1.1, 1), round(d * 1.2, 1)]

    pert = compute_pert(
        [TaskNode(id=n.id, title=n.title, duration=n.duration,
                  optimistic=n.optimistic, most_likely=n.most_likely, pessimistic=n.pessimistic,
                  status=n.status)
         for n in nodes],
        edges, targets or None,
    )

    # Tasks without duration
    tasks_missing_duration = [t.title for t in tasks if not t.duration_days and not (
        t.optimistic_duration and t.most_likely_duration and t.pessimistic_duration
    )]

    # Tasks without dependencies (orphans)
    dep_task_ids = set()
    for d in deps:
        dep_task_ids.add(str(d.predecessor_id))
        dep_task_ids.add(str(d.successor_id))
    orphan_tasks = [t.title for t in tasks if str(t.id) not in dep_task_ids]

    return {
        "project_name": project.name,
        "cpm": {
            "project_duration": cpm.project_duration,
            "critical_path": [
                {"id": t.id, "title": t.title, "duration": round(t.duration, 2),
                 "es": round(t.es, 2), "ef": round(t.ef, 2),
                 "ls": round(t.ls, 2), "lf": round(t.lf, 2)}
                for t in cpm.tasks if t.is_critical
            ],
            "has_cycle": cpm.has_cycle,
        },
        "pert": {
            "expected_duration": pert.project_expected_duration,
            "std_dev": pert.project_std_dev,
            "variance": pert.project_variance,
            "completion_probabilities": pert.completion_probabilities,
        },
        "tasks": [
            {
                "id": t.id, "title": t.title, "status": t.status,
                "duration": round(t.duration, 2),
                "es": round(t.es, 2), "ef": round(t.ef, 2),
                "ls": round(t.ls, 2), "lf": round(t.lf, 2),
                "total_float": round(t.total_float, 2),
                "free_float": round(t.free_float, 2),
                "is_critical": t.is_critical,
                "pert_expected": round(t.pert_expected, 2) if t.pert_expected else None,
                "pert_std_dev": round(t.pert_std_dev, 4) if t.pert_std_dev else None,
            }
            for t in cpm.tasks
        ],
        "dependencies": [
            {"predecessor_id": str(d.predecessor_id), "successor_id": str(d.successor_id),
             "type": d.dependency_type.value, "lag": d.lag_days}
            for d in deps
        ],
        "warnings": {
            "tasks_missing_duration": tasks_missing_duration,
            "orphan_tasks": orphan_tasks,
        },
    }


# ── Risk Report ─────────────────────────────────────────────────────

@router.get("/{project_id}/reports/risks")
async def report_risks(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    risks = (await db.execute(
        select(Risk).where(Risk.project_id == project_id).order_by(Risk.created_at.desc())
    )).scalars().all()

    # Build risk matrix counts
    prob_levels = ["very_low", "low", "medium", "high", "very_high"]
    impact_levels = ["very_low", "low", "medium", "high", "very_high"]
    matrix: dict[str, dict[str, int]] = {p: {i: 0 for i in impact_levels} for p in prob_levels}
    for r in risks:
        if r.status.value not in ("resolved", "closed"):
            matrix[r.probability.value][r.impact.value] += 1

    # Risk score mapping
    score_map = {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5}

    risk_list = []
    for r in risks:
        score = score_map.get(r.probability.value, 0) * score_map.get(r.impact.value, 0)
        risk_list.append({
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "category": r.category.value,
            "probability": r.probability.value,
            "impact": r.impact.value,
            "score": score,
            "status": r.status.value,
            "strategy": r.strategy.value,
            "response_plan": r.response_plan,
            "trigger_conditions": r.trigger_conditions,
        })

    # Sort by score descending
    risk_list.sort(key=lambda x: x["score"], reverse=True)

    by_category: dict[str, int] = {}
    by_strategy: dict[str, int] = {}
    for r in risks:
        by_category[r.category.value] = by_category.get(r.category.value, 0) + 1
        by_strategy[r.strategy.value] = by_strategy.get(r.strategy.value, 0) + 1

    return {
        "project_name": project.name,
        "total_risks": len(risks),
        "open_risks": sum(1 for r in risks if r.status.value not in ("resolved", "closed")),
        "risk_matrix": matrix,
        "by_category": by_category,
        "by_strategy": by_strategy,
        "risks": risk_list,
    }


# ── Performance Report ──────────────────────────────────────────────

@router.get("/{project_id}/reports/performance")
async def report_performance(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Task velocity
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    total_points = sum(t.story_points or 0 for t in tasks)
    done_points = sum(t.story_points or 0 for t in tasks if t.status.value == "done")
    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks if t.status.value == "done")
    blocked_tasks = sum(1 for t in tasks if t.status.value == "blocked")

    # Deliverable completion
    deliverables = (await db.execute(
        select(Deliverable).where(Deliverable.project_id == project_id)
    )).scalars().all()
    avg_completion = (
        sum(d.completion_percentage for d in deliverables) / len(deliverables)
        if deliverables else 0
    )

    # Measurements (KPIs)
    measurements = (await db.execute(
        select(Measurement).where(Measurement.project_id == project_id)
        .order_by(Measurement.created_at.desc())
    )).scalars().all()

    kpis = []
    for m in measurements:
        health = "gray"
        if m.actual_value is not None and m.target_value and m.target_value != 0:
            ratio = m.actual_value / m.target_value
            if ratio >= 0.9:
                health = "green"
            elif ratio >= 0.7:
                health = "yellow"
            else:
                health = "red"
        kpis.append({
            "name": m.name,
            "domain": m.domain.value,
            "metric_type": m.metric_type.value,
            "target": m.target_value,
            "actual": m.actual_value,
            "unit": m.unit,
            "health": health,
        })

    # Stakeholder engagement
    stakeholders = (await db.execute(
        select(Stakeholder).where(Stakeholder.project_id == project_id)
    )).scalars().all()

    engagement_gap = []
    for s in stakeholders:
        engagement_order = ["unaware", "resistant", "neutral", "supportive", "leading"]
        current_idx = engagement_order.index(s.engagement_level.value) if s.engagement_level.value in engagement_order else 0
        desired_idx = engagement_order.index(s.desired_engagement.value) if s.desired_engagement.value in engagement_order else 0
        gap = desired_idx - current_idx
        if gap > 0:
            engagement_gap.append({
                "name": s.name,
                "current": s.engagement_level.value,
                "desired": s.desired_engagement.value,
                "gap": gap,
            })
    engagement_gap.sort(key=lambda x: x["gap"], reverse=True)

    return {
        "project_name": project.name,
        "task_performance": {
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "blocked_tasks": blocked_tasks,
            "completion_pct": round(done_tasks / total_tasks * 100, 1) if total_tasks else 0,
            "total_story_points": total_points,
            "done_story_points": done_points,
            "velocity_pct": round(done_points / total_points * 100, 1) if total_points else 0,
        },
        "deliverable_performance": {
            "total": len(deliverables),
            "avg_completion_pct": round(avg_completion, 1),
            "items": [
                {
                    "name": d.name,
                    "status": d.status.value,
                    "quality": d.quality_level.value,
                    "completion_pct": d.completion_percentage,
                }
                for d in deliverables
            ],
        },
        "kpis": kpis,
        "stakeholder_engagement": {
            "total": len(stakeholders),
            "gaps": engagement_gap,
        },
    }
