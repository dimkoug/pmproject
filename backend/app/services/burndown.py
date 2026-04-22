"""Burndown / Burnup chart data calculator."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class BurndownPoint:
    date: str
    total: int
    remaining: int
    done: int
    ideal: float


def compute_burndown(tasks: list[dict], project_start: str | None = None) -> dict:
    """Compute burndown data from tasks with created_at and completed_date.

    Returns daily totals for burndown and burnup charts.
    """
    if not tasks:
        return {"points": [], "total_points": 0, "done_points": 0}

    total_points = sum(t.get("story_points", 0) or 1 for t in tasks)
    dates: dict[str, dict] = {}

    # Find date range
    all_dates = []
    for t in tasks:
        if t.get("created_at"):
            d = t["created_at"][:10] if isinstance(t["created_at"], str) else t["created_at"].strftime("%Y-%m-%d")
            all_dates.append(d)
        if t.get("completed_date"):
            d = t["completed_date"][:10] if isinstance(t["completed_date"], str) else t["completed_date"].strftime("%Y-%m-%d")
            all_dates.append(d)

    if not all_dates:
        return {"points": [], "total_points": total_points, "done_points": 0}

    start = min(all_dates)
    end = max(all_dates + [datetime.now(timezone.utc).strftime("%Y-%m-%d")])

    # Count completions per day
    completed_by_date: dict[str, int] = {}
    for t in tasks:
        if t.get("completed_date"):
            d = t["completed_date"][:10] if isinstance(t["completed_date"], str) else t["completed_date"].strftime("%Y-%m-%d")
            pts = t.get("story_points", 0) or 1
            completed_by_date[d] = completed_by_date.get(d, 0) + pts

    # Build daily points
    current = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    total_days = (end_dt - current).days or 1
    cumulative_done = 0
    points = []
    day_idx = 0

    while current <= end_dt:
        d = current.strftime("%Y-%m-%d")
        cumulative_done += completed_by_date.get(d, 0)
        ideal = total_points - (total_points * day_idx / total_days)
        points.append(BurndownPoint(
            date=d,
            total=total_points,
            remaining=total_points - cumulative_done,
            done=cumulative_done,
            ideal=round(ideal, 1),
        ))
        current += timedelta(days=1)
        day_idx += 1

    return {
        "points": [{"date": p.date, "total": p.total, "remaining": p.remaining, "done": p.done, "ideal": p.ideal} for p in points],
        "total_points": total_points,
        "done_points": cumulative_done,
    }
