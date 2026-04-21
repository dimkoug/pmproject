"""Resource leveling: detect over-allocated team members and suggest rescheduling."""

from dataclasses import dataclass


@dataclass
class OverAllocation:
    member_id: str
    member_name: str
    day: float
    hours_assigned: float
    capacity_hours: float
    tasks: list[str]


@dataclass
class LevelingResult:
    over_allocations: list[OverAllocation]
    suggestions: list[str]
    max_utilization: float


def detect_over_allocation(
    tasks: list[dict],
    members: list[dict],
    cpm_tasks: list[dict],
) -> LevelingResult:
    """Detect resource over-allocation based on CPM schedule.

    tasks: [{id, assignee_id, duration_days, title}]
    members: [{id, name, availability}]
    cpm_tasks: [{id, es, ef}]
    """
    cpm_map = {t["id"]: t for t in cpm_tasks}
    member_map = {m["id"]: m for m in members}

    # For each day, calculate hours per member
    max_day = max((ct.get("ef", 0) for ct in cpm_tasks), default=0)
    if max_day == 0:
        return LevelingResult(over_allocations=[], suggestions=[], max_utilization=0)

    # member_id -> day -> [task_titles]
    daily_load: dict[str, dict[int, list[str]]] = {}

    for t in tasks:
        if not t.get("assignee_id"):
            continue
        ct = cpm_map.get(t["id"])
        if not ct:
            continue
        es, ef = ct.get("es", 0), ct.get("ef", 0)
        mid = t["assignee_id"]
        if mid not in daily_load:
            daily_load[mid] = {}
        for day in range(int(es), int(ef)):
            daily_load[mid].setdefault(day, []).append(t["title"])

    over_allocs = []
    max_util = 0.0

    for mid, days in daily_load.items():
        member = member_map.get(mid)
        if not member:
            continue
        capacity = (member.get("availability", 100) / 100) * 8  # hours per day
        for day, task_titles in days.items():
            hours = len(task_titles) * 8  # each task = full day
            util = hours / capacity if capacity > 0 else 0
            max_util = max(max_util, util)
            if hours > capacity:
                over_allocs.append(OverAllocation(
                    member_id=mid, member_name=member.get("name", ""),
                    day=day, hours_assigned=hours, capacity_hours=capacity,
                    tasks=task_titles,
                ))

    suggestions = []
    if over_allocs:
        # Group by member
        by_member: dict[str, list[OverAllocation]] = {}
        for oa in over_allocs:
            by_member.setdefault(oa.member_name, []).append(oa)
        for name, allocs in by_member.items():
            task_set = set()
            for a in allocs:
                task_set.update(a.tasks)
            suggestions.append(
                f"{name} is over-allocated on {len(allocs)} day(s) across tasks: {', '.join(task_set)}. "
                f"Consider: reassigning tasks, staggering start dates, or reducing scope."
            )

    return LevelingResult(
        over_allocations=over_allocs,
        suggestions=suggestions,
        max_utilization=round(max_util * 100, 1),
    )
