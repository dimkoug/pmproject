"""Advanced features: Time tracking, Sprints, Baselines, Activity log, Search,
CSV import, PDF export, Custom fields, Dark mode, Monte Carlo, Resource leveling, Budget."""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.risk import Risk
from app.models.deliverable import Deliverable
from app.models.team_member import TeamMember
from app.models.time_entry import TimeEntry
from app.models.sprint import Sprint, SprintStatus
from app.models.schedule_baseline import ScheduleBaseline
from app.models.activity_log import ActivityLog
from app.models.custom_field import CustomField, CustomFieldValue, FieldType
from app.services.schedule import TaskNode, Dependency, compute_cpm
from app.services.monte_carlo import run_monte_carlo
from app.services.resource_leveling import detect_over_allocation

router = APIRouter(tags=["advanced"], dependencies=[Depends(get_current_user)])


# ── Time Tracking ───────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    project_id: UUID
    task_id: UUID
    hours: float
    work_date: str
    description: str | None = None


@router.get("/api/time-entries/")
async def list_time_entries(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimeEntry, User.name, Task.title)
        .join(User, TimeEntry.user_id == User.id, isouter=True)
        .join(Task, TimeEntry.task_id == Task.id, isouter=True)
        .where(TimeEntry.project_id == project_id)
        .order_by(TimeEntry.work_date.desc()).limit(200)
    )
    return [
        {"id": str(te.id), "task_id": str(te.task_id), "task_title": title,
         "user_name": name, "hours": te.hours, "work_date": te.work_date.isoformat()[:10],
         "description": te.description}
        for te, name, title in result.all()
    ]


@router.post("/api/time-entries/", status_code=201)
async def create_time_entry(
    payload: TimeEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    te = TimeEntry(
        project_id=payload.project_id, task_id=payload.task_id,
        user_id=current_user.id, hours=payload.hours,
        work_date=datetime.fromisoformat(payload.work_date),
        description=payload.description,
    )
    db.add(te)
    await db.commit()
    await db.refresh(te)
    return {"id": str(te.id), "hours": te.hours}


@router.get("/api/time-entries/summary")
async def time_summary(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task.title, func.sum(TimeEntry.hours))
        .join(Task, TimeEntry.task_id == Task.id)
        .where(TimeEntry.project_id == project_id)
        .group_by(Task.title)
    )
    by_task = [{"task": r[0], "hours": round(r[1], 1)} for r in result.all()]
    total = sum(r["hours"] for r in by_task)
    return {"total_hours": round(total, 1), "by_task": by_task}


# ── Sprints ─────────────────────────────────────────────────────────

class SprintCreate(BaseModel):
    project_id: UUID
    name: str
    goal: str | None = None
    sprint_number: int = 1
    start_date: str | None = None
    end_date: str | None = None


@router.get("/api/sprints/")
async def list_sprints(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.sprint_number)
    )
    sprints = result.scalars().all()
    out = []
    for s in sprints:
        # Count tasks in sprint
        task_count = await db.scalar(
            select(func.count(Task.id)).where(Task.sprint_id == s.id)
        ) or 0
        done_count = await db.scalar(
            select(func.count(Task.id)).where(Task.sprint_id == s.id, cast(Task.status, String) == "DONE")
        ) or 0
        total_pts = await db.scalar(
            select(func.coalesce(func.sum(Task.story_points), 0)).where(Task.sprint_id == s.id)
        ) or 0
        done_pts = await db.scalar(
            select(func.coalesce(func.sum(Task.story_points), 0))
            .where(Task.sprint_id == s.id, cast(Task.status, String) == "DONE")
        ) or 0
        out.append({
            "id": str(s.id), "name": s.name, "goal": s.goal, "status": s.status.value,
            "sprint_number": s.sprint_number,
            "start_date": s.start_date.isoformat()[:10] if s.start_date else None,
            "end_date": s.end_date.isoformat()[:10] if s.end_date else None,
            "total_tasks": task_count, "done_tasks": done_count,
            "total_points": total_pts, "done_points": done_pts,
        })
    return out


@router.post("/api/sprints/", status_code=201)
async def create_sprint(payload: SprintCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    sprint = Sprint(
        project_id=payload.project_id, name=payload.name, goal=payload.goal,
        sprint_number=payload.sprint_number,
        start_date=datetime.fromisoformat(payload.start_date) if payload.start_date else None,
        end_date=datetime.fromisoformat(payload.end_date) if payload.end_date else None,
    )
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return {"id": str(sprint.id), "name": sprint.name}


@router.patch("/api/sprints/{sprint_id}")
async def update_sprint(sprint_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    sprint.status = SprintStatus(status)
    if status == "completed":
        # Calculate completed points
        done_pts = await db.scalar(
            select(func.coalesce(func.sum(Task.story_points), 0))
            .where(Task.sprint_id == sprint.id, cast(Task.status, String) == "DONE")
        ) or 0
        sprint.completed_points = done_pts
    await db.commit()
    return {"id": str(sprint.id), "status": sprint.status.value}


@router.get("/api/sprints/velocity")
async def sprint_velocity(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Sprint).where(Sprint.project_id == project_id, Sprint.status == SprintStatus.COMPLETED)
        .order_by(Sprint.sprint_number)
    )
    sprints = result.scalars().all()
    return [
        {"sprint": s.name, "number": s.sprint_number, "points": s.completed_points or 0}
        for s in sprints
    ]


# ── Schedule Baselines ──────────────────────────────────────────────

@router.get("/api/projects/{project_id}/baselines")
async def list_baselines(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScheduleBaseline).where(ScheduleBaseline.project_id == project_id)
        .order_by(ScheduleBaseline.created_at.desc())
    )
    return [
        {"id": str(b.id), "name": b.name, "created_at": b.created_at.isoformat(),
         "project_duration": b.snapshot.get("project_duration", 0),
         "task_count": len(b.snapshot.get("tasks", []))}
        for b in result.scalars().all()
    ]


@router.post("/api/projects/{project_id}/baselines", status_code=201)
async def save_baseline(project_id: UUID, name: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Save current CPM schedule as a named baseline."""
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()

    nodes = [TaskNode(id=str(t.id), title=t.title, duration=t.duration_days or 0,
                      optimistic=t.optimistic_duration, most_likely=t.most_likely_duration,
                      pessimistic=t.pessimistic_duration, status=t.status.value) for t in tasks]
    edges = [Dependency(predecessor_id=str(d.predecessor_id), successor_id=str(d.successor_id),
                        dep_type=d.dependency_type.value, lag=d.lag_days) for d in deps]

    cpm = compute_cpm(nodes, edges)
    snapshot = {
        "project_duration": cpm.project_duration,
        "critical_path": cpm.critical_path,
        "tasks": [{"id": t.id, "title": t.title, "duration": t.duration, "es": t.es, "ef": t.ef,
                    "ls": t.ls, "lf": t.lf, "total_float": t.total_float, "is_critical": t.is_critical}
                   for t in cpm.tasks],
    }
    baseline = ScheduleBaseline(project_id=project_id, name=name, snapshot=snapshot)
    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return {"id": str(baseline.id), "name": baseline.name, "project_duration": cpm.project_duration}


@router.get("/api/projects/{project_id}/baselines/{baseline_id}/compare")
async def compare_baseline(project_id: UUID, baseline_id: UUID, db: AsyncSession = Depends(get_db)):
    """Compare current schedule against a saved baseline."""
    baseline = await db.get(ScheduleBaseline, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    # Current CPM
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()
    nodes = [TaskNode(id=str(t.id), title=t.title, duration=t.duration_days or 0, status=t.status.value) for t in tasks]
    edges = [Dependency(predecessor_id=str(d.predecessor_id), successor_id=str(d.successor_id),
                        dep_type=d.dependency_type.value, lag=d.lag_days) for d in deps]
    current = compute_cpm(nodes, edges)

    baseline_map = {t["id"]: t for t in baseline.snapshot.get("tasks", [])}
    current_map = {t.id: t for t in current.tasks}

    comparison = []
    for tid in set(list(baseline_map.keys()) + list(current_map.keys())):
        bl = baseline_map.get(tid)
        cu = current_map.get(tid)
        comparison.append({
            "id": tid,
            "title": (cu.title if cu else bl.get("title", "")) if cu or bl else "",
            "baseline_duration": bl.get("duration", 0) if bl else None,
            "current_duration": round(cu.duration, 2) if cu else None,
            "baseline_es": bl.get("es", 0) if bl else None,
            "current_es": round(cu.es, 2) if cu else None,
            "baseline_ef": bl.get("ef", 0) if bl else None,
            "current_ef": round(cu.ef, 2) if cu else None,
            "duration_variance": round(cu.duration - bl.get("duration", 0), 2) if cu and bl else None,
            "schedule_variance": round(cu.ef - bl.get("ef", 0), 2) if cu and bl else None,
        })

    return {
        "baseline_name": baseline.name,
        "baseline_duration": baseline.snapshot.get("project_duration", 0),
        "current_duration": current.project_duration,
        "variance": round(current.project_duration - baseline.snapshot.get("project_duration", 0), 2),
        "tasks": comparison,
    }


# ── Activity Log ────────────────────────────────────────────────────

@router.get("/api/projects/{project_id}/activity")
async def get_activity(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ActivityLog, User.name)
        .join(User, ActivityLog.user_id == User.id, isouter=True)
        .where(ActivityLog.project_id == project_id)
        .order_by(ActivityLog.created_at.desc())
        .offset(skip).limit(limit)
    )
    return [
        {"id": str(a.id), "action": a.action, "entity_type": a.entity_type,
         "entity_name": a.entity_name, "details": a.details,
         "user_name": name, "created_at": a.created_at.isoformat()}
        for a, name in result.all()
    ]


# ── Global Search ───────────────────────────────────────────────────

@router.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"
    results = []

    # Search tasks
    tq = select(Task.id, Task.title, Task.project_id).where(Task.title.ilike(pattern))
    if project_id:
        tq = tq.where(Task.project_id == project_id)
    for row in (await db.execute(tq.limit(20))).all():
        results.append({"type": "task", "id": str(row[0]), "title": row[1], "project_id": str(row[2])})

    # Search risks
    rq = select(Risk.id, Risk.title, Risk.project_id).where(Risk.title.ilike(pattern))
    if project_id:
        rq = rq.where(Risk.project_id == project_id)
    for row in (await db.execute(rq.limit(20))).all():
        results.append({"type": "risk", "id": str(row[0]), "title": row[1], "project_id": str(row[2])})

    # Search deliverables
    dq = select(Deliverable.id, Deliverable.name, Deliverable.project_id).where(Deliverable.name.ilike(pattern))
    if project_id:
        dq = dq.where(Deliverable.project_id == project_id)
    for row in (await db.execute(dq.limit(20))).all():
        results.append({"type": "deliverable", "id": str(row[0]), "title": row[1], "project_id": str(row[2])})

    # Search projects
    pq = select(Project.id, Project.name).where(Project.name.ilike(pattern))
    for row in (await db.execute(pq.limit(10))).all():
        results.append({"type": "project", "id": str(row[0]), "title": row[1], "project_id": str(row[0])})

    return results


# ── CSV Import ──────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/import/csv")
async def import_csv(
    project_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import tasks from CSV. Columns: title, description, status, priority, duration_days, story_points, planned_cost"""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    for row in reader:
        title = row.get("title", "").strip()
        if not title:
            continue
        task = Task(
            project_id=project_id,
            title=title,
            description=row.get("description", "").strip() or None,
            status=row.get("status", "backlog").strip().lower() or "backlog",
            priority=row.get("priority", "medium").strip().lower() or "medium",
            duration_days=float(row["duration_days"]) if row.get("duration_days") else None,
            story_points=int(row["story_points"]) if row.get("story_points") else None,
            planned_cost=float(row["planned_cost"]) if row.get("planned_cost") else None,
        )
        db.add(task)
        created += 1

    await db.commit()
    return {"message": f"{created} tasks imported", "count": created}


# ── PDF Export ──────────────────────────────────────────────────────

@router.get("/api/projects/{project_id}/export/pdf")
async def export_pdf(project_id: UUID, db: AsyncSession = Depends(get_db)):
    from fpdf import FPDF

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    risks = (await db.execute(select(Risk).where(Risk.project_id == project_id))).scalars().all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Project Report: {project.name}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Status: {project.status.value} | Approach: {project.development_approach.value} | Budget: ${project.budget or 0:,.0f}", ln=True)
    pdf.ln(5)

    # Tasks table
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Tasks ({len(tasks)})", ln=True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(70, 6, "Title", 1)
    pdf.cell(25, 6, "Status", 1)
    pdf.cell(25, 6, "Priority", 1)
    pdf.cell(25, 6, "Duration", 1)
    pdf.cell(25, 6, "Cost", 1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for t in tasks:
        pdf.cell(70, 6, t.title[:35], 1)
        pdf.cell(25, 6, t.status.value, 1)
        pdf.cell(25, 6, t.priority.value, 1)
        pdf.cell(25, 6, f"{t.duration_days or '-'}d", 1)
        pdf.cell(25, 6, f"${t.planned_cost or 0:,.0f}", 1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Risks ({len(risks)})", ln=True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(60, 6, "Title", 1)
    pdf.cell(30, 6, "Category", 1)
    pdf.cell(25, 6, "Probability", 1)
    pdf.cell(25, 6, "Impact", 1)
    pdf.cell(25, 6, "Strategy", 1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for r in risks:
        pdf.cell(60, 6, r.title[:30], 1)
        pdf.cell(30, 6, r.category.value, 1)
        pdf.cell(25, 6, r.probability.value, 1)
        pdf.cell(25, 6, r.impact.value, 1)
        pdf.cell(25, 6, r.strategy.value, 1)
        pdf.ln()

    output = io.BytesIO(pdf.output())
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={project.name.replace(' ', '_')}_report.pdf"},
    )


# ── Custom Fields ───────────────────────────────────────────────────

class CustomFieldCreate(BaseModel):
    project_id: UUID
    name: str
    field_type: FieldType = FieldType.TEXT
    entity_type: str  # task, risk, deliverable
    options: str | None = None


@router.get("/api/custom-fields/")
async def list_custom_fields(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CustomField).where(CustomField.project_id == project_id)
    )
    return [
        {"id": str(f.id), "name": f.name, "field_type": f.field_type.value,
         "entity_type": f.entity_type, "options": f.options}
        for f in result.scalars().all()
    ]


@router.post("/api/custom-fields/", status_code=201)
async def create_custom_field(payload: CustomFieldCreate, db: AsyncSession = Depends(get_db)):
    field = CustomField(
        project_id=payload.project_id, name=payload.name,
        field_type=payload.field_type, entity_type=payload.entity_type,
        options=payload.options,
    )
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return {"id": str(field.id), "name": field.name}


@router.get("/api/custom-fields/{field_id}/values")
async def get_field_values(field_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CustomFieldValue).where(CustomFieldValue.field_id == field_id)
    )
    return {str(v.entity_id): v.value for v in result.scalars().all()}


@router.put("/api/custom-fields/{field_id}/values/{entity_id}")
async def set_field_value(field_id: UUID, entity_id: UUID, value: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CustomFieldValue).where(CustomFieldValue.field_id == field_id, CustomFieldValue.entity_id == entity_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = value
    else:
        db.add(CustomFieldValue(field_id=field_id, entity_id=entity_id, value=value))
    await db.commit()
    return {"ok": True}


# ── Dark Mode Toggle ────────────────────────────────────────────────

@router.post("/api/auth/dark-mode")
async def toggle_dark_mode(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.dark_mode = not current_user.dark_mode
    await db.commit()
    return {"dark_mode": current_user.dark_mode}


# ── Monte Carlo ─────────────────────────────────────────────────────

@router.get("/api/projects/{project_id}/monte-carlo")
async def get_monte_carlo(
    project_id: UUID,
    iterations: int = Query(1000, ge=100, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Synchronous Monte Carlo — kept for backward compatibility & small runs."""
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()

    task_data = [
        {"id": str(t.id), "title": t.title, "duration": t.duration_days or 0,
         "optimistic": t.optimistic_duration, "most_likely": t.most_likely_duration,
         "pessimistic": t.pessimistic_duration, "planned_cost": t.planned_cost}
        for t in tasks
    ]
    dep_data = [
        {"predecessor_id": str(d.predecessor_id), "successor_id": str(d.successor_id)}
        for d in deps
    ]

    result = run_monte_carlo(task_data, dep_data, iterations)
    return {
        "iterations": result.iterations,
        "duration": {
            "mean": result.duration_mean, "min": result.duration_min, "max": result.duration_max,
            "p10": result.duration_p10, "p50": result.duration_p50, "p75": result.duration_p75,
            "p90": result.duration_p90, "p95": result.duration_p95,
        },
        "cost": {"mean": result.cost_mean, "p50": result.cost_p50, "p90": result.cost_p90},
        "histogram": result.histogram,
    }


# ── Async Monte Carlo (Celery) ──────────────────────────────────────

@router.post("/api/projects/{project_id}/monte-carlo/async")
async def start_monte_carlo_async(
    project_id: UUID,
    iterations: int = Query(1000, ge=100, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Submit a Monte Carlo simulation to Celery for large iteration counts."""
    from app.tasks import run_monte_carlo_task

    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()

    task_data = [
        {"id": str(t.id), "title": t.title, "duration": t.duration_days or 0,
         "optimistic": t.optimistic_duration, "most_likely": t.most_likely_duration,
         "pessimistic": t.pessimistic_duration, "planned_cost": t.planned_cost}
        for t in tasks
    ]
    dep_data = [
        {"predecessor_id": str(d.predecessor_id), "successor_id": str(d.successor_id)}
        for d in deps
    ]

    result = run_monte_carlo_task.delay(task_data, dep_data, iterations)
    return {"task_id": result.id, "status": "submitted"}


@router.get("/api/celery-tasks/{task_id}")
async def get_celery_task_status(task_id: str):
    """Poll a Celery task result by ID."""
    from app.celery_app import celery as celery_app

    result = celery_app.AsyncResult(task_id)
    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    return response


# ── Resource Leveling ───────────────────────────────────────────────

@router.get("/api/projects/{project_id}/resource-leveling")
async def get_resource_leveling(project_id: UUID, db: AsyncSession = Depends(get_db)):
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == project_id))).scalars().all()
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == project_id))).scalars().all()

    # Run CPM first
    nodes = [TaskNode(id=str(t.id), title=t.title, duration=t.duration_days or 0, status=t.status.value) for t in tasks]
    edges = [Dependency(predecessor_id=str(d.predecessor_id), successor_id=str(d.successor_id),
                        dep_type=d.dependency_type.value, lag=d.lag_days) for d in deps]
    cpm = compute_cpm(nodes, edges)

    task_data = [{"id": str(t.id), "title": t.title, "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                  "duration_days": t.duration_days} for t in tasks]
    member_data = [{"id": str(m.id), "name": m.name, "availability": m.availability} for m in members]
    cpm_data = [{"id": t.id, "es": t.es, "ef": t.ef} for t in cpm.tasks]

    result = detect_over_allocation(task_data, member_data, cpm_data)
    return {
        "max_utilization": result.max_utilization,
        "over_allocations": [
            {"member": oa.member_name, "day": oa.day, "hours": oa.hours_assigned,
             "capacity": oa.capacity_hours, "tasks": oa.tasks}
            for oa in result.over_allocations
        ],
        "suggestions": result.suggestions,
    }


# ── Budget by Phase ─────────────────────────────────────────────────

@router.get("/api/projects/{project_id}/budget")
async def get_budget_breakdown(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()

    by_status: dict[str, dict] = {}
    for t in tasks:
        s = t.status.value
        if s not in by_status:
            by_status[s] = {"planned": 0, "actual": 0, "count": 0}
        by_status[s]["planned"] += t.planned_cost or 0
        by_status[s]["actual"] += t.actual_cost or 0
        by_status[s]["count"] += 1

    total_planned = sum(t.planned_cost or 0 for t in tasks)
    total_actual = sum(t.actual_cost or 0 for t in tasks)

    return {
        "project_budget": project.budget or 0,
        "total_planned": round(total_planned, 2),
        "total_actual": round(total_actual, 2),
        "remaining": round((project.budget or 0) - total_actual, 2),
        "by_status": {k: {"planned": round(v["planned"], 2), "actual": round(v["actual"], 2), "count": v["count"]}
                      for k, v in by_status.items()},
    }
