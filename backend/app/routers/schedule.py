from collections import defaultdict, deque
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.task import Task
from app.models.task_dependency import TaskDependency, DependencyType
from app.schemas.task import DependencyCreate, DependencyRead
from app.services.schedule import TaskNode, Dependency, compute_cpm, compute_pert

router = APIRouter(prefix="/api/projects", tags=["schedule"], dependencies=[Depends(get_current_user)])


# ── Validation helpers ──────────────────────────────────────────────

async def _detect_cycle(
    project_id: UUID,
    new_pred_id: UUID,
    new_succ_id: UUID,
    db: AsyncSession,
) -> bool:
    """Return True if adding new_pred -> new_succ would create a cycle."""
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.project_id == project_id)
    )
    existing = result.scalars().all()

    adj: dict[str, list[str]] = defaultdict(list)
    all_nodes: set[str] = set()
    for d in existing:
        adj[str(d.predecessor_id)].append(str(d.successor_id))
        all_nodes.add(str(d.predecessor_id))
        all_nodes.add(str(d.successor_id))

    # Add the proposed edge
    adj[str(new_pred_id)].append(str(new_succ_id))
    all_nodes.add(str(new_pred_id))
    all_nodes.add(str(new_succ_id))

    # BFS-based cycle detection (topological sort)
    in_degree: dict[str, int] = {n: 0 for n in all_nodes}
    for src, targets in adj.items():
        for tgt in targets:
            in_degree[tgt] += 1

    queue = deque(n for n, d in in_degree.items() if d == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for succ in adj.get(node, []):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    return visited != len(all_nodes)


# ── Task Dependencies CRUD ──────────────────────────────────────────

@router.get("/{project_id}/dependencies", response_model=list[DependencyRead])
async def list_dependencies(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.project_id == project_id)
    )
    return result.scalars().all()


@router.post("/{project_id}/dependencies", response_model=DependencyRead, status_code=201)
async def create_dependency(
    project_id: UUID,
    payload: DependencyCreate,
    db: AsyncSession = Depends(get_db),
):
    # 1. Self-dependency
    if payload.predecessor_id == payload.successor_id:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself")

    # 2. Tasks exist and belong to project
    pred = await db.get(Task, payload.predecessor_id)
    succ = await db.get(Task, payload.successor_id)
    if not pred or not succ:
        raise HTTPException(status_code=404, detail="Predecessor or successor task not found")
    if str(pred.project_id) != str(project_id) or str(succ.project_id) != str(project_id):
        raise HTTPException(status_code=400, detail="Both tasks must belong to this project")

    # 3. Duplicate check
    existing = await db.execute(
        select(TaskDependency)
        .where(TaskDependency.predecessor_id == payload.predecessor_id)
        .where(TaskDependency.successor_id == payload.successor_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"'{pred.title}' is already a predecessor of '{succ.title}'",
        )

    # 4. Reverse duplicate check (B->A already exists, can't add A->B)
    reverse = await db.execute(
        select(TaskDependency)
        .where(TaskDependency.predecessor_id == payload.successor_id)
        .where(TaskDependency.successor_id == payload.predecessor_id)
    )
    if reverse.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Reverse dependency already exists: '{succ.title}' is a predecessor of '{pred.title}'",
        )

    # 5. Circular dependency detection
    has_cycle = await _detect_cycle(project_id, payload.predecessor_id, payload.successor_id, db)
    if has_cycle:
        raise HTTPException(
            status_code=400,
            detail=f"Adding this dependency would create a circular dependency. "
                   f"'{succ.title}' already depends (directly or indirectly) on '{pred.title}' through other tasks.",
        )

    # 6. Lag validation. Negative lag (aka "lead time") is allowed on every
    # dependency type — it just means the successor starts before the
    # predecessor finishes (standard MS Project semantics). We only reject
    # leads that are longer than the predecessor's own duration, because a
    # successor can't legitimately start before its predecessor exists.
    if payload.lag_days < 0:
        pred_dur = pred.duration_days or pred.most_likely_duration or 0
        if pred_dur and abs(payload.lag_days) > pred_dur:
            raise HTTPException(
                status_code=400,
                detail=f"Lead time ({abs(payload.lag_days)} days) cannot exceed the predecessor duration ({pred_dur} days)",
            )

    # 7. Dependency type validation
    dep_type = payload.dependency_type
    pred_dur = pred.duration_days or pred.most_likely_duration or 0
    succ_dur = succ.duration_days or succ.most_likely_duration or 0

    if dep_type == DependencyType.SF and pred_dur == 0 and succ_dur == 0:
        raise HTTPException(
            status_code=400,
            detail="Start-to-Finish (SF) requires at least one task to have a duration",
        )

    dep = TaskDependency(
        project_id=project_id,
        predecessor_id=payload.predecessor_id,
        successor_id=payload.successor_id,
        dependency_type=payload.dependency_type,
        lag_days=payload.lag_days,
    )
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return dep


@router.delete("/{project_id}/dependencies/{dep_id}", status_code=204)
async def delete_dependency(project_id: UUID, dep_id: UUID, db: AsyncSession = Depends(get_db)):
    dep = await db.get(TaskDependency, dep_id)
    if not dep or str(dep.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Dependency not found")
    await db.delete(dep)
    await db.commit()


# ── CPM Analysis ────────────────────────────────────────────────────

async def _load_network(project_id: UUID, db: AsyncSession):
    """Load tasks and dependencies for a project, return (TaskNode list, Dependency list)."""
    tasks_result = await db.execute(
        select(Task).where(Task.project_id == project_id)
    )
    tasks = tasks_result.scalars().all()

    deps_result = await db.execute(
        select(TaskDependency).where(TaskDependency.project_id == project_id)
    )
    deps = deps_result.scalars().all()

    nodes = [
        TaskNode(
            id=str(t.id),
            title=t.title,
            duration=t.duration_days or 0,
            optimistic=t.optimistic_duration,
            most_likely=t.most_likely_duration,
            pessimistic=t.pessimistic_duration,
            status=t.status.value,
        )
        for t in tasks
    ]

    edges = [
        Dependency(
            predecessor_id=str(d.predecessor_id),
            successor_id=str(d.successor_id),
            dep_type=d.dependency_type.value,
            lag=d.lag_days,
        )
        for d in deps
    ]

    return nodes, edges


@router.get("/{project_id}/cpm")
async def get_cpm_analysis(project_id: UUID, db: AsyncSession = Depends(get_db)):
    nodes, edges = await _load_network(project_id, db)
    if not nodes:
        return {"tasks": [], "critical_path": [], "project_duration": 0, "has_cycle": False}

    result = compute_cpm(nodes, edges)

    return {
        "project_duration": result.project_duration,
        "critical_path": result.critical_path,
        "has_cycle": result.has_cycle,
        "cycle_message": result.cycle_message if result.has_cycle else None,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "duration": t.duration,
                "es": round(t.es, 2),
                "ef": round(t.ef, 2),
                "ls": round(t.ls, 2),
                "lf": round(t.lf, 2),
                "total_float": round(t.total_float, 2),
                "free_float": round(t.free_float, 2),
                "is_critical": t.is_critical,
                "status": t.status,
            }
            for t in result.tasks
        ],
    }


# ── PERT Analysis ───────────────────────────────────────────────────

@router.get("/{project_id}/pert")
async def get_pert_analysis(
    project_id: UUID,
    target_durations: str = Query("", description="Comma-separated target durations, e.g. 30,35,40"),
    db: AsyncSession = Depends(get_db),
):
    nodes, edges = await _load_network(project_id, db)
    if not nodes:
        return {
            "tasks": [], "critical_path": [], "project_expected_duration": 0,
            "project_std_dev": 0, "project_variance": 0, "completion_probabilities": {},
        }

    targets = []
    if target_durations:
        try:
            targets = [float(x.strip()) for x in target_durations.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="target_durations must be comma-separated numbers")

    result = compute_pert(nodes, edges, targets or None)

    return {
        "project_expected_duration": result.project_expected_duration,
        "project_std_dev": result.project_std_dev,
        "project_variance": result.project_variance,
        "critical_path": result.critical_path,
        "has_cycle": result.has_cycle,
        "completion_probabilities": result.completion_probabilities,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "duration": round(t.duration, 2),
                "optimistic": t.optimistic,
                "most_likely": t.most_likely,
                "pessimistic": t.pessimistic,
                "pert_expected": round(t.pert_expected, 2) if t.pert_expected else None,
                "pert_std_dev": round(t.pert_std_dev, 4) if t.pert_std_dev else None,
                "pert_variance": round(t.pert_variance, 4) if t.pert_variance else None,
                "es": round(t.es, 2),
                "ef": round(t.ef, 2),
                "ls": round(t.ls, 2),
                "lf": round(t.lf, 2),
                "total_float": round(t.total_float, 2),
                "is_critical": t.is_critical,
                "status": t.status,
            }
            for t in result.tasks
        ],
    }
