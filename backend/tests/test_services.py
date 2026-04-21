"""Unit tests for service modules: EVM, CPM/PERT, Monte Carlo, Burndown, Resource Leveling, Auth."""

import pytest
from datetime import datetime, timedelta

from app.services.evm import compute_evm, EVMResult
from app.services.schedule import (
    TaskNode, Dependency, compute_cpm, compute_pert,
    _topological_sort, _compute_pert_estimates,
)
from app.services.monte_carlo import run_monte_carlo
from app.services.burndown import compute_burndown
from app.services.resource_leveling import detect_over_allocation
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


# ═══════════════════════════════════════════════════════════════════
# EVM (Earned Value Management) Tests
# ═══════════════════════════════════════════════════════════════════

class TestEVM:
    def test_all_tasks_done(self):
        tasks = [
            {"planned_cost": 1000, "actual_cost": 900, "status": "done"},
            {"planned_cost": 2000, "actual_cost": 2100, "status": "done"},
        ]
        result = compute_evm(tasks)
        assert result.bac == 3000
        assert result.pv == 3000
        assert result.ev == 3000  # all done
        assert result.ac == 3000
        assert result.sv == 0  # on schedule
        assert result.spi == 1.0

    def test_in_progress_50_percent_rule(self):
        tasks = [
            {"planned_cost": 1000, "actual_cost": 500, "status": "in_progress"},
        ]
        result = compute_evm(tasks)
        assert result.ev == 500  # 50% rule
        assert result.pv == 1000
        assert result.ac == 500
        assert result.sv == -500

    def test_in_review_50_percent_rule(self):
        tasks = [
            {"planned_cost": 2000, "actual_cost": 1800, "status": "in_review"},
        ]
        result = compute_evm(tasks)
        assert result.ev == 1000  # 50% rule

    def test_backlog_and_todo_earn_nothing(self):
        tasks = [
            {"planned_cost": 1000, "actual_cost": 0, "status": "backlog"},
            {"planned_cost": 1000, "actual_cost": 0, "status": "todo"},
            {"planned_cost": 1000, "actual_cost": 0, "status": "blocked"},
        ]
        result = compute_evm(tasks)
        assert result.ev == 0

    def test_mixed_statuses(self):
        tasks = [
            {"planned_cost": 1000, "actual_cost": 1000, "status": "done"},
            {"planned_cost": 1000, "actual_cost": 600, "status": "in_progress"},
            {"planned_cost": 1000, "actual_cost": 0, "status": "backlog"},
        ]
        result = compute_evm(tasks)
        assert result.bac == 3000
        assert result.ev == 1500  # 1000 + 500
        assert result.ac == 1600
        assert result.cv == -100  # over budget
        assert result.sv == -1500  # behind schedule

    def test_custom_project_budget(self):
        tasks = [
            {"planned_cost": 500, "actual_cost": 400, "status": "done"},
        ]
        result = compute_evm(tasks, project_budget=10000)
        assert result.bac == 10000

    def test_empty_tasks(self):
        result = compute_evm([])
        assert result.bac == 0
        assert result.ev == 0
        assert result.ac == 0
        assert result.spi == 0
        assert result.cpi == 0
        assert result.percent_complete == 0

    def test_zero_actual_cost_cpi(self):
        tasks = [
            {"planned_cost": 1000, "actual_cost": 0, "status": "done"},
        ]
        result = compute_evm(tasks)
        assert result.cpi == 0  # avoid division by zero

    def test_none_costs_treated_as_zero(self):
        tasks = [
            {"planned_cost": None, "actual_cost": None, "status": "done"},
        ]
        result = compute_evm(tasks)
        assert result.bac == 0
        assert result.ev == 0

    def test_percent_complete_and_spent(self):
        tasks = [
            {"planned_cost": 500, "actual_cost": 300, "status": "done"},
            {"planned_cost": 500, "actual_cost": 200, "status": "backlog"},
        ]
        result = compute_evm(tasks)
        assert result.percent_complete == 50.0  # 500/1000
        assert result.percent_spent == 50.0  # 500/1000

    def test_eac_etc_vac_tcpi(self):
        tasks = [
            {"planned_cost": 2000, "actual_cost": 1500, "status": "done"},
            {"planned_cost": 2000, "actual_cost": 500, "status": "in_progress"},
        ]
        result = compute_evm(tasks)
        # ev=3000, ac=2000, bac=4000, cpi=1.5
        assert result.eac == round(4000 / 1.5, 2)
        assert result.etc == round(result.eac - 2000, 2)
        assert result.vac == round(4000 - result.eac, 2)


# ═══════════════════════════════════════════════════════════════════
# CPM (Critical Path Method) Tests
# ═══════════════════════════════════════════════════════════════════

class TestCPM:
    def test_single_task(self):
        nodes = [TaskNode(id="A", title="Task A", duration=5)]
        result = compute_cpm(nodes, [])
        assert result.project_duration == 5
        assert result.critical_path == ["A"]
        assert result.has_cycle is False

    def test_sequential_tasks(self):
        nodes = [
            TaskNode(id="A", title="Task A", duration=3),
            TaskNode(id="B", title="Task B", duration=5),
            TaskNode(id="C", title="Task C", duration=2),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="B", successor_id="C"),
        ]
        result = compute_cpm(nodes, deps)
        assert result.project_duration == 10  # 3+5+2
        assert result.critical_path == ["A", "B", "C"]

    def test_parallel_tasks_critical_path(self):
        nodes = [
            TaskNode(id="A", title="Start", duration=2),
            TaskNode(id="B", title="Path 1", duration=5),
            TaskNode(id="C", title="Path 2", duration=3),
            TaskNode(id="D", title="End", duration=1),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="A", successor_id="C"),
            Dependency(predecessor_id="B", successor_id="D"),
            Dependency(predecessor_id="C", successor_id="D"),
        ]
        result = compute_cpm(nodes, deps)
        assert result.project_duration == 8  # A(2)+B(5)+D(1)
        assert "A" in result.critical_path
        assert "B" in result.critical_path
        assert "D" in result.critical_path
        assert "C" not in result.critical_path

    def test_float_calculation(self):
        nodes = [
            TaskNode(id="A", title="Start", duration=2),
            TaskNode(id="B", title="Long", duration=5),
            TaskNode(id="C", title="Short", duration=3),
            TaskNode(id="D", title="End", duration=1),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="A", successor_id="C"),
            Dependency(predecessor_id="B", successor_id="D"),
            Dependency(predecessor_id="C", successor_id="D"),
        ]
        result = compute_cpm(nodes, deps)
        task_map = {t.id: t for t in result.tasks}
        assert task_map["B"].total_float == 0  # critical
        assert task_map["C"].total_float == 2  # 2 days of float

    def test_cycle_detection(self):
        nodes = [
            TaskNode(id="A", title="A", duration=1),
            TaskNode(id="B", title="B", duration=1),
            TaskNode(id="C", title="C", duration=1),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="B", successor_id="C"),
            Dependency(predecessor_id="C", successor_id="A"),  # cycle
        ]
        result = compute_cpm(nodes, deps)
        assert result.has_cycle is True
        assert result.project_duration == 0

    def test_no_tasks(self):
        result = compute_cpm([], [])
        assert result.project_duration == 0
        assert result.critical_path == []

    def test_lag_time(self):
        nodes = [
            TaskNode(id="A", title="A", duration=3),
            TaskNode(id="B", title="B", duration=2),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B", lag=2),
        ]
        result = compute_cpm(nodes, deps)
        assert result.project_duration == 7  # 3 + 2(lag) + 2

    def test_start_to_start_dependency(self):
        nodes = [
            TaskNode(id="A", title="A", duration=4),
            TaskNode(id="B", title="B", duration=3),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B", dep_type="start_to_start"),
        ]
        result = compute_cpm(nodes, deps)
        task_map = {t.id: t for t in result.tasks}
        assert task_map["B"].es == 0  # starts when A starts

    def test_finish_to_finish_dependency(self):
        nodes = [
            TaskNode(id="A", title="A", duration=5),
            TaskNode(id="B", title="B", duration=3),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B", dep_type="finish_to_finish"),
        ]
        result = compute_cpm(nodes, deps)
        task_map = {t.id: t for t in result.tasks}
        assert task_map["B"].ef == 5  # finishes when A finishes


# ═══════════════════════════════════════════════════════════════════
# PERT Tests
# ═══════════════════════════════════════════════════════════════════

class TestPERT:
    def test_pert_expected_duration(self):
        node = TaskNode(id="A", title="A", duration=0, optimistic=2, most_likely=5, pessimistic=14)
        _compute_pert_estimates(node)
        # Te = (2 + 4*5 + 14) / 6 = 36/6 = 6
        assert node.pert_expected == 6.0
        assert node.pert_std_dev == 2.0  # (14-2)/6
        assert node.pert_variance == 4.0
        assert node.duration == 6.0  # should override 0

    def test_pert_does_not_override_explicit_duration(self):
        node = TaskNode(id="A", title="A", duration=10, optimistic=2, most_likely=5, pessimistic=14)
        _compute_pert_estimates(node)
        assert node.duration == 10  # keeps explicit

    def test_pert_with_no_estimates(self):
        node = TaskNode(id="A", title="A", duration=5)
        _compute_pert_estimates(node)
        assert node.pert_expected is None
        assert node.duration == 5

    def test_compute_pert_full(self):
        nodes = [
            TaskNode(id="A", title="A", duration=0, optimistic=1, most_likely=3, pessimistic=5),
            TaskNode(id="B", title="B", duration=0, optimistic=2, most_likely=4, pessimistic=12),
        ]
        deps = [Dependency(predecessor_id="A", successor_id="B")]
        result = compute_pert(nodes, deps, target_durations=[10, 15, 20])
        assert result.project_expected_duration > 0
        assert result.project_std_dev >= 0
        assert result.project_variance >= 0
        assert len(result.completion_probabilities) == 3
        assert result.has_cycle is False

    def test_pert_with_cycle(self):
        nodes = [
            TaskNode(id="A", title="A", duration=5),
            TaskNode(id="B", title="B", duration=3),
        ]
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="B", successor_id="A"),
        ]
        result = compute_pert(nodes, deps)
        assert result.has_cycle is True

    def test_pert_completion_probability(self):
        nodes = [
            TaskNode(id="A", title="A", duration=0, optimistic=4, most_likely=6, pessimistic=8),
        ]
        result = compute_pert(nodes, [], target_durations=[6])
        # Expected = 6, should be ~50%
        assert 45 < result.completion_probabilities[6] < 55

    def test_pert_zero_std_dev(self):
        """When all tasks have same O, M, P values, std_dev is 0."""
        nodes = [
            TaskNode(id="A", title="A", duration=0, optimistic=5, most_likely=5, pessimistic=5),
        ]
        result = compute_pert(nodes, [], target_durations=[5, 10])
        assert result.project_std_dev == 0
        assert result.completion_probabilities[5] == 100.0
        assert result.completion_probabilities[10] == 100.0


# ═══════════════════════════════════════════════════════════════════
# Topological Sort Tests
# ═══════════════════════════════════════════════════════════════════

class TestTopologicalSort:
    def test_simple_chain(self):
        nodes = {"A": TaskNode(id="A", title="A", duration=1),
                 "B": TaskNode(id="B", title="B", duration=1),
                 "C": TaskNode(id="C", title="C", duration=1)}
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="B", successor_id="C"),
        ]
        order = _topological_sort(nodes, deps)
        assert order is not None
        assert order.index("A") < order.index("B") < order.index("C")

    def test_cycle_returns_none(self):
        nodes = {"A": TaskNode(id="A", title="A", duration=1),
                 "B": TaskNode(id="B", title="B", duration=1)}
        deps = [
            Dependency(predecessor_id="A", successor_id="B"),
            Dependency(predecessor_id="B", successor_id="A"),
        ]
        assert _topological_sort(nodes, deps) is None

    def test_independent_tasks(self):
        nodes = {"A": TaskNode(id="A", title="A", duration=1),
                 "B": TaskNode(id="B", title="B", duration=1)}
        order = _topological_sort(nodes, [])
        assert order is not None
        assert len(order) == 2


# ═══════════════════════════════════════════════════════════════════
# Monte Carlo Tests
# ═══════════════════════════════════════════════════════════════════

class TestMonteCarlo:
    def test_basic_simulation(self):
        tasks = [
            {"id": "A", "duration": 5, "optimistic": 3, "most_likely": 5, "pessimistic": 10, "planned_cost": 1000},
            {"id": "B", "duration": 3, "optimistic": 2, "most_likely": 3, "pessimistic": 6, "planned_cost": 500},
        ]
        deps = [{"predecessor_id": "A", "successor_id": "B"}]
        result = run_monte_carlo(tasks, deps, iterations=500)
        assert result.iterations == 500
        assert result.duration_mean > 0
        assert result.duration_min <= result.duration_p50 <= result.duration_max
        assert result.duration_p10 <= result.duration_p90
        assert result.cost_mean > 0
        assert len(result.histogram) == 10

    def test_no_dependencies(self):
        tasks = [
            {"id": "A", "duration": 5, "planned_cost": 100},
            {"id": "B", "duration": 3, "planned_cost": 200},
        ]
        result = run_monte_carlo(tasks, [], iterations=100)
        assert result.duration_mean > 0
        assert result.cost_mean > 0

    def test_single_task(self):
        tasks = [{"id": "A", "duration": 10, "planned_cost": 5000}]
        result = run_monte_carlo(tasks, [], iterations=100)
        # No variation since O=M=P=10
        assert result.duration_min == result.duration_max == 10

    def test_percentiles_ordered(self):
        tasks = [
            {"id": "A", "duration": 5, "optimistic": 2, "most_likely": 5, "pessimistic": 15, "planned_cost": 1000},
        ]
        result = run_monte_carlo(tasks, [], iterations=1000)
        assert result.duration_p10 <= result.duration_p50
        assert result.duration_p50 <= result.duration_p75
        assert result.duration_p75 <= result.duration_p90
        assert result.duration_p90 <= result.duration_p95

    def test_zero_cost_tasks(self):
        tasks = [{"id": "A", "duration": 5, "planned_cost": 0}]
        result = run_monte_carlo(tasks, [], iterations=100)
        assert result.cost_mean == 0


# ═══════════════════════════════════════════════════════════════════
# Burndown Tests
# ═══════════════════════════════════════════════════════════════════

class TestBurndown:
    def test_empty_tasks(self):
        result = compute_burndown([])
        assert result["points"] == []
        assert result["total_points"] == 0

    def test_no_dates(self):
        result = compute_burndown([{"story_points": 5}])
        assert result["points"] == []

    def test_basic_burndown(self):
        tasks = [
            {"story_points": 3, "created_at": "2024-01-01", "completed_date": "2024-01-03"},
            {"story_points": 5, "created_at": "2024-01-01", "completed_date": "2024-01-05"},
            {"story_points": 2, "created_at": "2024-01-01", "completed_date": None},
        ]
        result = compute_burndown(tasks)
        assert result["total_points"] == 10
        assert result["done_points"] == 8
        assert len(result["points"]) > 0

    def test_burndown_daily_points(self):
        tasks = [
            {"story_points": 5, "created_at": "2024-01-01", "completed_date": "2024-01-02"},
        ]
        result = compute_burndown(tasks)
        points = result["points"]
        # First day: nothing done
        assert points[0]["remaining"] == 5
        assert points[0]["done"] == 0
        # After completion date
        assert points[1]["remaining"] == 0
        assert points[1]["done"] == 5

    def test_tasks_without_story_points_default_to_1(self):
        tasks = [
            {"created_at": "2024-01-01", "completed_date": "2024-01-02"},
            {"created_at": "2024-01-01", "completed_date": None},
        ]
        result = compute_burndown(tasks)
        assert result["total_points"] == 2  # each defaults to 1

    def test_ideal_line(self):
        tasks = [
            {"story_points": 10, "created_at": "2024-01-01", "completed_date": "2024-01-05"},
        ]
        result = compute_burndown(tasks)
        points = result["points"]
        # Ideal should decrease linearly
        assert points[0]["ideal"] == 10  # start at total


# ═══════════════════════════════════════════════════════════════════
# Resource Leveling Tests
# ═══════════════════════════════════════════════════════════════════

class TestResourceLeveling:
    def test_no_over_allocation(self):
        tasks = [{"id": "T1", "assignee_id": "M1", "title": "Task 1", "duration_days": 2}]
        members = [{"id": "M1", "name": "Alice", "availability": 100}]
        cpm_tasks = [{"id": "T1", "es": 0, "ef": 2}]
        result = detect_over_allocation(tasks, members, cpm_tasks)
        assert len(result.over_allocations) == 0
        assert result.max_utilization == 100.0

    def test_over_allocation_detected(self):
        tasks = [
            {"id": "T1", "assignee_id": "M1", "title": "Task 1", "duration_days": 3},
            {"id": "T2", "assignee_id": "M1", "title": "Task 2", "duration_days": 3},
        ]
        members = [{"id": "M1", "name": "Alice", "availability": 100}]
        cpm_tasks = [
            {"id": "T1", "es": 0, "ef": 3},
            {"id": "T2", "es": 0, "ef": 3},  # overlapping
        ]
        result = detect_over_allocation(tasks, members, cpm_tasks)
        assert len(result.over_allocations) > 0
        assert result.max_utilization > 100
        assert len(result.suggestions) > 0

    def test_unassigned_tasks_ignored(self):
        tasks = [{"id": "T1", "assignee_id": None, "title": "Unassigned", "duration_days": 5}]
        members = [{"id": "M1", "name": "Alice", "availability": 100}]
        cpm_tasks = [{"id": "T1", "es": 0, "ef": 5}]
        result = detect_over_allocation(tasks, members, cpm_tasks)
        assert len(result.over_allocations) == 0

    def test_empty_cpm_tasks(self):
        result = detect_over_allocation([], [], [])
        assert result.max_utilization == 0

    def test_part_time_member(self):
        tasks = [
            {"id": "T1", "assignee_id": "M1", "title": "Task 1", "duration_days": 2},
            {"id": "T2", "assignee_id": "M1", "title": "Task 2", "duration_days": 2},
        ]
        members = [{"id": "M1", "name": "Bob", "availability": 50}]  # 50% = 4 hours/day
        cpm_tasks = [
            {"id": "T1", "es": 0, "ef": 2},
            {"id": "T2", "es": 0, "ef": 2},
        ]
        result = detect_over_allocation(tasks, members, cpm_tasks)
        assert len(result.over_allocations) > 0  # 16h needed, only 4h capacity

    def test_suggestions_contain_member_name(self):
        tasks = [
            {"id": "T1", "assignee_id": "M1", "title": "Task A", "duration_days": 2},
            {"id": "T2", "assignee_id": "M1", "title": "Task B", "duration_days": 2},
        ]
        members = [{"id": "M1", "name": "Charlie", "availability": 100}]
        cpm_tasks = [
            {"id": "T1", "es": 0, "ef": 2},
            {"id": "T2", "es": 0, "ef": 2},
        ]
        result = detect_over_allocation(tasks, members, cpm_tasks)
        assert any("Charlie" in s for s in result.suggestions)


# ═══════════════════════════════════════════════════════════════════
# Auth Service Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuthService:
    def test_hash_and_verify_password(self):
        password = "my_secure_password123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_unique(self):
        p1 = hash_password("same_password")
        p2 = hash_password("same_password")
        assert p1 != p2  # bcrypt salts differently each time

    def test_create_and_decode_token(self):
        data = {"sub": "user@test.com"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user@test.com"
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_token_with_custom_expiry(self):
        data = {"sub": "user@test.com"}
        token = create_access_token(data, expires_delta=timedelta(minutes=5))
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user@test.com"

    def test_expired_token(self):
        data = {"sub": "user@test.com"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        result = decode_access_token(token)
        assert result is None
