"""CPM (Critical Path Method) and PERT (Program Evaluation and Review Technique) engine.

CPM calculates:
  - Forward pass: Early Start (ES), Early Finish (EF)
  - Backward pass: Late Start (LS), Late Finish (LF)
  - Total Float (slack) = LS - ES
  - Critical Path: tasks where float == 0

PERT calculates:
  - Expected duration Te = (O + 4M + P) / 6
  - Standard deviation sigma = (P - O) / 6
  - Variance = sigma^2
  - Project completion probability using normal distribution
"""

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class TaskNode:
    id: str
    title: str
    duration: float  # effective duration (PERT expected or explicit)
    optimistic: float | None = None
    most_likely: float | None = None
    pessimistic: float | None = None
    status: str = ""
    # CPM computed fields
    es: float = 0.0  # Early Start
    ef: float = 0.0  # Early Finish
    ls: float = float("inf")  # Late Start
    lf: float = float("inf")  # Late Finish
    total_float: float = 0.0
    free_float: float = 0.0
    is_critical: bool = False
    # PERT computed fields
    pert_expected: float | None = None
    pert_std_dev: float | None = None
    pert_variance: float | None = None


@dataclass
class Dependency:
    predecessor_id: str
    successor_id: str
    dep_type: str = "finish_to_start"
    lag: float = 0.0


@dataclass
class CPMResult:
    tasks: list[TaskNode]
    critical_path: list[str]  # ordered task IDs on critical path
    project_duration: float
    has_cycle: bool = False
    cycle_message: str = ""


@dataclass
class PERTResult:
    tasks: list[TaskNode]
    critical_path: list[str]
    project_expected_duration: float
    project_std_dev: float
    project_variance: float
    completion_probabilities: dict[float, float] = field(default_factory=dict)
    has_cycle: bool = False


def _topological_sort(nodes: dict[str, TaskNode], edges: list[Dependency]) -> list[str] | None:
    """Returns topological order of node IDs, or None if cycle detected."""
    in_degree: dict[str, int] = {nid: 0 for nid in nodes}
    adj: dict[str, list[str]] = defaultdict(list)

    for dep in edges:
        if dep.predecessor_id in nodes and dep.successor_id in nodes:
            adj[dep.predecessor_id].append(dep.successor_id)
            in_degree[dep.successor_id] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for succ in adj[nid]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(order) != len(nodes):
        return None  # cycle
    return order


def _compute_pert_estimates(node: TaskNode) -> None:
    """Compute PERT expected duration, std dev, and variance for a task."""
    if node.optimistic is not None and node.most_likely is not None and node.pessimistic is not None:
        node.pert_expected = (node.optimistic + 4 * node.most_likely + node.pessimistic) / 6
        node.pert_std_dev = (node.pessimistic - node.optimistic) / 6
        node.pert_variance = node.pert_std_dev ** 2
        # Use PERT expected as effective duration if no explicit duration set
        if node.duration == 0:
            node.duration = node.pert_expected


def _build_adj(edges: list[Dependency], nodes: dict[str, TaskNode]):
    """Build adjacency lists for successors and predecessors."""
    successors: dict[str, list[Dependency]] = defaultdict(list)
    predecessors: dict[str, list[Dependency]] = defaultdict(list)
    for dep in edges:
        if dep.predecessor_id in nodes and dep.successor_id in nodes:
            successors[dep.predecessor_id].append(dep)
            predecessors[dep.successor_id].append(dep)
    return successors, predecessors


def compute_cpm(
    task_nodes: list[TaskNode],
    dependencies: list[Dependency],
) -> CPMResult:
    """Run full CPM analysis: forward pass, backward pass, identify critical path."""
    nodes = {t.id: t for t in task_nodes}

    # Compute PERT estimates first (sets effective duration)
    for node in nodes.values():
        _compute_pert_estimates(node)

    topo_order = _topological_sort(nodes, dependencies)
    if topo_order is None:
        return CPMResult(
            tasks=list(nodes.values()),
            critical_path=[],
            project_duration=0,
            has_cycle=True,
            cycle_message="Circular dependency detected in task network",
        )

    successors, predecessors = _build_adj(dependencies, nodes)

    # Forward pass: compute ES and EF
    for nid in topo_order:
        node = nodes[nid]
        if nid in predecessors:
            for dep in predecessors[nid]:
                pred = nodes[dep.predecessor_id]
                if dep.dep_type == "finish_to_start":
                    candidate = pred.ef + dep.lag
                elif dep.dep_type == "start_to_start":
                    candidate = pred.es + dep.lag
                elif dep.dep_type == "finish_to_finish":
                    candidate = pred.ef + dep.lag - node.duration
                elif dep.dep_type == "start_to_finish":
                    candidate = pred.es + dep.lag - node.duration
                else:
                    candidate = pred.ef + dep.lag
                node.es = max(node.es, candidate)
        node.ef = node.es + node.duration

    # Project duration
    project_duration = max((n.ef for n in nodes.values()), default=0)

    # Backward pass: compute LF and LS
    for node in nodes.values():
        node.lf = project_duration  # default for nodes with no successors

    for nid in reversed(topo_order):
        node = nodes[nid]
        if nid in successors:
            for dep in successors[nid]:
                succ = nodes[dep.successor_id]
                if dep.dep_type == "finish_to_start":
                    candidate = succ.ls - dep.lag
                elif dep.dep_type == "start_to_start":
                    candidate = succ.ls - dep.lag + node.duration
                elif dep.dep_type == "finish_to_finish":
                    candidate = succ.lf - dep.lag
                elif dep.dep_type == "start_to_finish":
                    candidate = succ.lf - dep.lag + node.duration
                else:
                    candidate = succ.ls - dep.lag
                node.lf = min(node.lf, candidate)
        node.ls = node.lf - node.duration

    # Calculate float and identify critical path
    for node in nodes.values():
        node.total_float = round(node.ls - node.es, 4)
        node.is_critical = abs(node.total_float) < 0.0001

    # Free float
    for nid in topo_order:
        node = nodes[nid]
        if nid in successors:
            min_succ_es = min(
                nodes[dep.successor_id].es - dep.lag for dep in successors[nid]
            )
            node.free_float = round(min_succ_es - node.ef, 4)
        else:
            node.free_float = round(project_duration - node.ef, 4)

    # Extract critical path in order
    critical_path = [nid for nid in topo_order if nodes[nid].is_critical]

    return CPMResult(
        tasks=list(nodes.values()),
        critical_path=critical_path,
        project_duration=round(project_duration, 2),
    )


def _normal_cdf(x: float) -> float:
    """Approximate cumulative distribution function for standard normal."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def compute_pert(
    task_nodes: list[TaskNode],
    dependencies: list[Dependency],
    target_durations: list[float] | None = None,
) -> PERTResult:
    """Run PERT analysis on top of CPM results.

    Calculates project-level expected duration, variance, and
    probability of completing within target durations.
    """
    cpm_result = compute_cpm(task_nodes, dependencies)

    if cpm_result.has_cycle:
        return PERTResult(
            tasks=cpm_result.tasks,
            critical_path=[],
            project_expected_duration=0,
            project_std_dev=0,
            project_variance=0,
            has_cycle=True,
        )

    nodes = {t.id: t for t in cpm_result.tasks}

    # Project variance = sum of variances on critical path
    project_variance = sum(
        nodes[tid].pert_variance
        for tid in cpm_result.critical_path
        if nodes[tid].pert_variance is not None
    )
    project_std_dev = math.sqrt(project_variance) if project_variance > 0 else 0

    # Completion probabilities for target durations
    probabilities: dict[float, float] = {}
    targets = target_durations or []
    for target in targets:
        if project_std_dev > 0:
            z = (target - cpm_result.project_duration) / project_std_dev
            probabilities[target] = round(_normal_cdf(z) * 100, 2)
        else:
            probabilities[target] = 100.0 if target >= cpm_result.project_duration else 0.0

    return PERTResult(
        tasks=cpm_result.tasks,
        critical_path=cpm_result.critical_path,
        project_expected_duration=cpm_result.project_duration,
        project_std_dev=round(project_std_dev, 4),
        project_variance=round(project_variance, 4),
        completion_probabilities=probabilities,
    )
