"""Monte Carlo simulation for project schedule and cost forecasting.
Uses triangular distribution (O, M, P) to simulate thousands of project outcomes."""

import random
import math
from dataclasses import dataclass


@dataclass
class MonteCarloResult:
    iterations: int
    duration_mean: float
    duration_p10: float
    duration_p50: float
    duration_p75: float
    duration_p90: float
    duration_p95: float
    duration_min: float
    duration_max: float
    cost_mean: float
    cost_p50: float
    cost_p90: float
    histogram: list[dict]  # [{bucket: "28-30", count: 150}, ...]


def _triangular_sample(o: float, m: float, p: float) -> float:
    """Sample from triangular distribution."""
    return random.triangular(o, p, m)


def _simulate_once(
    tasks: list[dict],
    adj: dict[str, list[str]],
    predecessors: dict[str, list[str]],
) -> tuple[float, float]:
    """Run one simulation iteration. Returns (total_duration, total_cost)."""
    durations: dict[str, float] = {}
    costs: dict[str, float] = {}

    for t in tasks:
        tid = t["id"]
        o = t.get("optimistic") or t.get("duration", 0)
        m = t.get("most_likely") or t.get("duration", 0)
        p = t.get("pessimistic") or t.get("duration", 0)
        if o and m and p and o < p:
            durations[tid] = _triangular_sample(o, m, p)
        else:
            durations[tid] = t.get("duration", 0)

        pc = t.get("planned_cost", 0) or 0
        if pc > 0:
            # Cost varies +/- 20% triangular
            costs[tid] = _triangular_sample(pc * 0.8, pc, pc * 1.3)
        else:
            costs[tid] = 0

    # Forward pass to get project duration
    es: dict[str, float] = {}
    task_ids = [t["id"] for t in tasks]
    # Topological order (simple BFS)
    in_deg = {tid: 0 for tid in task_ids}
    for tid in task_ids:
        for pred in predecessors.get(tid, []):
            if pred in in_deg:
                in_deg[tid] = in_deg.get(tid, 0)  # already counted

    # Recalc in-degrees
    in_deg = {tid: len([p for p in predecessors.get(tid, []) if p in set(task_ids)]) for tid in task_ids}
    from collections import deque
    queue = deque(tid for tid, d in in_deg.items() if d == 0)
    order = []
    while queue:
        tid = queue.popleft()
        order.append(tid)
        for succ in adj.get(tid, []):
            if succ in in_deg:
                in_deg[succ] -= 1
                if in_deg[succ] == 0:
                    queue.append(succ)

    for tid in order:
        pred_finish = max((es.get(p, 0) + durations.get(p, 0) for p in predecessors.get(tid, []) if p in es), default=0)
        es[tid] = pred_finish

    project_duration = max((es.get(tid, 0) + durations.get(tid, 0) for tid in task_ids), default=0)
    project_cost = sum(costs.values())

    return project_duration, project_cost


def run_monte_carlo(
    tasks: list[dict],
    dependencies: list[dict],
    iterations: int = 1000,
) -> MonteCarloResult:
    """Run Monte Carlo simulation."""
    adj: dict[str, list[str]] = {}
    predecessors: dict[str, list[str]] = {}
    for d in dependencies:
        adj.setdefault(d["predecessor_id"], []).append(d["successor_id"])
        predecessors.setdefault(d["successor_id"], []).append(d["predecessor_id"])

    dur_results: list[float] = []
    cost_results: list[float] = []

    for _ in range(iterations):
        dur, cost = _simulate_once(tasks, adj, predecessors)
        dur_results.append(dur)
        cost_results.append(cost)

    dur_results.sort()
    cost_results.sort()

    def percentile(data: list[float], p: float) -> float:
        idx = int(len(data) * p / 100)
        return round(data[min(idx, len(data) - 1)], 2)

    # Histogram (10 buckets)
    histogram = []
    if dur_results:
        min_d, max_d = dur_results[0], dur_results[-1]
        bucket_size = max((max_d - min_d) / 10, 0.1)
        for i in range(10):
            lo = min_d + i * bucket_size
            hi = lo + bucket_size
            count = sum(1 for d in dur_results if lo <= d < hi + (0.01 if i == 9 else 0))
            histogram.append({"bucket": f"{lo:.0f}-{hi:.0f}", "count": count, "lo": round(lo, 1), "hi": round(hi, 1)})

    return MonteCarloResult(
        iterations=iterations,
        duration_mean=round(sum(dur_results) / len(dur_results), 2) if dur_results else 0,
        duration_p10=percentile(dur_results, 10),
        duration_p50=percentile(dur_results, 50),
        duration_p75=percentile(dur_results, 75),
        duration_p90=percentile(dur_results, 90),
        duration_p95=percentile(dur_results, 95),
        duration_min=round(dur_results[0], 2) if dur_results else 0,
        duration_max=round(dur_results[-1], 2) if dur_results else 0,
        cost_mean=round(sum(cost_results) / len(cost_results), 2) if cost_results else 0,
        cost_p50=percentile(cost_results, 50),
        cost_p90=percentile(cost_results, 90),
        histogram=histogram,
    )
