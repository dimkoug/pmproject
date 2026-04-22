"""AI project-plan generation (#52).

Two endpoints:
  * POST /api/projects/{id}/ai-plan/start  → enqueues a Celery task on the
    `reports` queue, returns task_id for polling via /api/celery-tasks/{id}.
  * POST /api/projects/{id}/ai-plan/commit → takes an accepted plan dict and
    creates the corresponding tasks / risks / deliverables in one transaction.

Generation is deliberately separate from commit so the user can edit before
saving (or just discard).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import has_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.project import Project
from app.models.risk import Risk, RiskImpact, RiskProbability
from app.models.task import Task, TaskStatus
from app.models.user import User

router = APIRouter(prefix="/api/projects", tags=["ai-plan"], dependencies=[Depends(get_current_user)])


class AiPlanStart(BaseModel):
    brief: str


class AiPlanTask(BaseModel):
    title: str
    description: str | None = None
    estimate_hours: float | None = None


class AiPlanRisk(BaseModel):
    title: str
    impact: str | None = "med"  # low|med|high
    likelihood: str | None = "med"


class AiPlanMilestone(BaseModel):
    title: str
    target_offset_days: int | None = None


class AiPlanDeliverable(BaseModel):
    title: str
    description: str | None = None


class AiPlanCommit(BaseModel):
    summary: str | None = None
    tasks: list[AiPlanTask] = []
    risks: list[AiPlanRisk] = []
    milestones: list[AiPlanMilestone] = []
    deliverables: list[AiPlanDeliverable] = []


def _impact_from_str(s: str | None) -> RiskImpact:
    s = (s or "med").lower()
    if s in ("low", "minor", "minimal"):
        return RiskImpact.LOW
    if s in ("high", "major", "severe", "critical"):
        return RiskImpact.HIGH
    return RiskImpact.MEDIUM


def _likelihood_from_str(s: str | None) -> RiskProbability:
    s = (s or "med").lower()
    if s in ("low", "rare", "unlikely"):
        return RiskProbability.LOW
    if s in ("high", "likely", "frequent"):
        return RiskProbability.HIGH
    return RiskProbability.MEDIUM


@router.post("/{project_id}/ai-plan/start")
async def start_ai_plan(
    project_id: UUID,
    p: AiPlanStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not await has_permission(db, current_user, "projects.task.create", project_id=project_id):
        raise HTTPException(403, "Need projects.task.create on this project")
    brief = (p.brief or "").strip()
    if not brief:
        raise HTTPException(400, "Brief is required")
    if len(brief) > 4000:
        raise HTTPException(400, "Brief too long (max 4000 chars)")

    from app.tasks import generate_project_plan_task
    result = generate_project_plan_task.delay(brief)
    return {"task_id": result.id, "status": "submitted"}


@router.post("/{project_id}/ai-plan/commit")
async def commit_ai_plan(
    project_id: UUID,
    p: AiPlanCommit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not await has_permission(db, current_user, "projects.task.create", project_id=project_id):
        raise HTTPException(403, "Need projects.task.create on this project")

    created: dict[str, int] = {"tasks": 0, "risks": 0, "deliverables": 0, "milestones": 0}
    base_date = project.start_date or datetime.utcnow()

    # Tasks
    for t in p.tasks:
        if not t.title.strip():
            continue
        duration_days = None
        if t.estimate_hours:
            duration_days = round(t.estimate_hours / 8.0, 2)
        task = Task(
            project_id=project_id,
            title=t.title.strip(),
            description=t.description,
            status=TaskStatus.BACKLOG,
            duration_days=duration_days,
        )
        db.add(task)
        created["tasks"] += 1

    # Milestones — modeled as zero-duration tasks for now (no separate milestone table)
    for m in p.milestones:
        if not m.title.strip():
            continue
        target = base_date + timedelta(days=m.target_offset_days or 0) if m.target_offset_days else None
        task = Task(
            project_id=project_id,
            title=f"🎯 {m.title.strip()}",
            description="Milestone (auto-created from AI plan)",
            status=TaskStatus.BACKLOG,
            duration_days=0,
            due_date=target,
        )
        db.add(task)
        created["milestones"] += 1

    # Risks
    for r in p.risks:
        if not r.title.strip():
            continue
        risk = Risk(
            project_id=project_id,
            title=r.title.strip()[:255],
            impact=_impact_from_str(r.impact),
            probability=_likelihood_from_str(r.likelihood),
        )
        db.add(risk)
        created["risks"] += 1

    # Deliverables
    for d in p.deliverables:
        if not d.title.strip():
            continue
        deliv = Deliverable(
            project_id=project_id,
            name=d.title.strip()[:255],
            description=d.description,
            status=DeliverableStatus.PLANNED,
        )
        db.add(deliv)
        created["deliverables"] += 1

    await db.commit()
    return {"created": created, "summary": p.summary}
