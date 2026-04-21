from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.project_template import ProjectTemplate
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.risk import Risk
from app.models.stakeholder import Stakeholder

router = APIRouter(prefix="/api/templates", tags=["templates"], dependencies=[Depends(get_current_user)])


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    source_project_id: UUID


@router.get("/")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectTemplate).order_by(ProjectTemplate.created_at.desc()))
    return [
        {"id": str(t.id), "name": t.name, "description": t.description, "created_at": t.created_at.isoformat()}
        for t in result.scalars().all()
    ]


@router.post("/", status_code=201)
async def create_template(payload: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """Save a project as a reusable template (tasks, risks, dependencies structure)."""
    project = await db.get(Project, payload.source_project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Source project not found")

    tasks = (await db.execute(select(Task).where(Task.project_id == payload.source_project_id))).scalars().all()
    risks = (await db.execute(select(Risk).where(Risk.project_id == payload.source_project_id))).scalars().all()
    deps = (await db.execute(select(TaskDependency).where(TaskDependency.project_id == payload.source_project_id))).scalars().all()

    template_data = {
        "development_approach": project.development_approach.value,
        "tasks": [
            {"title": t.title, "description": t.description, "wbs_code": t.wbs_code,
             "priority": t.priority.value, "is_milestone": t.is_milestone,
             "duration_days": t.duration_days, "planned_cost": t.planned_cost,
             "optimistic_duration": t.optimistic_duration, "most_likely_duration": t.most_likely_duration,
             "pessimistic_duration": t.pessimistic_duration, "original_id": str(t.id),
             "parent_original_id": str(t.parent_id) if t.parent_id else None}
            for t in tasks
        ],
        "risks": [
            {"title": r.title, "description": r.description, "category": r.category.value,
             "probability": r.probability.value, "impact": r.impact.value,
             "strategy": r.strategy.value, "response_plan": r.response_plan}
            for r in risks
        ],
        "dependencies": [
            {"predecessor_original_id": str(d.predecessor_id), "successor_original_id": str(d.successor_id),
             "dependency_type": d.dependency_type.value, "lag_days": d.lag_days}
            for d in deps
        ],
    }

    tmpl = ProjectTemplate(name=payload.name, description=payload.description, template_data=template_data)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return {"id": str(tmpl.id), "name": tmpl.name}


@router.post("/{template_id}/apply")
async def apply_template(template_id: UUID, project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Apply a template to an existing project, creating tasks/risks/dependencies."""
    tmpl = await db.get(ProjectTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data = tmpl.template_data
    id_map: dict[str, UUID] = {}  # original_id -> new_id

    # Create tasks
    for t_data in data.get("tasks", []):
        task = Task(
            project_id=project_id, title=t_data["title"], description=t_data.get("description"),
            wbs_code=t_data.get("wbs_code"), priority=t_data.get("priority", "medium"),
            is_milestone=t_data.get("is_milestone", False), duration_days=t_data.get("duration_days"),
            planned_cost=t_data.get("planned_cost"),
            optimistic_duration=t_data.get("optimistic_duration"),
            most_likely_duration=t_data.get("most_likely_duration"),
            pessimistic_duration=t_data.get("pessimistic_duration"),
        )
        db.add(task)
        await db.flush()
        id_map[t_data["original_id"]] = task.id

    # Set parent_ids
    for t_data in data.get("tasks", []):
        if t_data.get("parent_original_id") and t_data["parent_original_id"] in id_map:
            new_id = id_map[t_data["original_id"]]
            task = await db.get(Task, new_id)
            if task:
                task.parent_id = id_map[t_data["parent_original_id"]]

    # Create dependencies
    for d_data in data.get("dependencies", []):
        pred_id = id_map.get(d_data["predecessor_original_id"])
        succ_id = id_map.get(d_data["successor_original_id"])
        if pred_id and succ_id:
            dep = TaskDependency(
                project_id=project_id, predecessor_id=pred_id, successor_id=succ_id,
                dependency_type=d_data.get("dependency_type", "finish_to_start"),
                lag_days=d_data.get("lag_days", 0),
            )
            db.add(dep)

    # Create risks
    for r_data in data.get("risks", []):
        risk = Risk(
            project_id=project_id, title=r_data["title"], description=r_data.get("description"),
            category=r_data.get("category", "technical"), probability=r_data.get("probability", "medium"),
            impact=r_data.get("impact", "medium"), strategy=r_data.get("strategy", "mitigate"),
            response_plan=r_data.get("response_plan"),
        )
        db.add(risk)

    await db.commit()
    return {"message": f"Template applied: {len(id_map)} tasks, {len(data.get('risks', []))} risks created"}


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    tmpl = await db.get(ProjectTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(tmpl)
    await db.commit()
