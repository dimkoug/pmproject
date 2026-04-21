"""Gantt chart data builder. Converts tasks + dependencies + CPM results into
a timeline structure the frontend can render as horizontal bars."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class GanttBar:
    id: str
    title: str
    wbs_code: str | None
    parent_id: str | None
    start_day: float
    end_day: float
    duration: float
    status: str
    is_critical: bool
    is_milestone: bool
    assignee: str | None
    progress: float  # 0-100
    dependencies: list[str]  # predecessor IDs


def build_gantt_data(
    cpm_tasks: list[dict],
    dependencies: list[dict],
    tasks_raw: list[dict],
) -> list[GanttBar]:
    """Build Gantt bars from CPM results and raw task data."""
    raw_map = {t["id"]: t for t in tasks_raw}
    dep_map: dict[str, list[str]] = {}
    for d in dependencies:
        succ = d["successor_id"]
        dep_map.setdefault(succ, []).append(d["predecessor_id"])

    bars = []
    for ct in cpm_tasks:
        raw = raw_map.get(ct["id"], {})
        status = ct.get("status", raw.get("status", ""))
        progress = 100.0 if status == "done" else 50.0 if status in ("in_progress", "in_review") else 0.0

        bars.append(GanttBar(
            id=ct["id"],
            title=ct["title"],
            wbs_code=raw.get("wbs_code"),
            parent_id=raw.get("parent_id"),
            start_day=ct.get("es", 0),
            end_day=ct.get("ef", 0),
            duration=ct.get("duration", 0),
            status=status,
            is_critical=ct.get("is_critical", False),
            is_milestone=raw.get("is_milestone", False),
            assignee=raw.get("assignee_name"),
            progress=progress,
            dependencies=dep_map.get(ct["id"], []),
        ))

    return bars
