import pytest

from app.database import Base
from app.models.project import Project, DevelopmentApproach, ProjectStatus, DeliveryCadence
from app.models.stakeholder import Stakeholder, EngagementLevel, StakeholderCategory
from app.models.team_member import TeamMember, TeamRole
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.risk import Risk, RiskCategory, RiskProbability, RiskImpact, RiskStatus, RiskStrategy
from app.models.deliverable import Deliverable, DeliverableStatus, QualityLevel
from app.models.measurement import Measurement, MetricType, MeasurementDomain
from app.models.change_request import ChangeRequest, ChangeStatus, ChangeImpact


class TestDatabaseTables:
    def test_all_tables_registered(self):
        tables = set(Base.metadata.tables.keys())
        expected = {
            "projects", "stakeholders", "team_members", "tasks",
            "risks", "deliverables", "measurements", "change_requests",
        }
        assert expected == tables

    def test_table_count(self):
        assert len(Base.metadata.tables) == 8


class TestProjectEnums:
    def test_development_approaches(self):
        values = [e.value for e in DevelopmentApproach]
        assert "predictive" in values
        assert "adaptive" in values
        assert "hybrid" in values
        assert "agile" in values
        assert len(values) == 4

    def test_project_statuses(self):
        values = [e.value for e in ProjectStatus]
        expected = ["initiating", "planning", "executing", "monitoring", "closing", "closed"]
        assert values == expected

    def test_delivery_cadences(self):
        values = [e.value for e in DeliveryCadence]
        assert "single" in values
        assert "multiple" in values
        assert "periodic" in values
        assert len(values) == 3


class TestStakeholderEnums:
    def test_engagement_levels(self):
        values = [e.value for e in EngagementLevel]
        expected = ["unaware", "resistant", "neutral", "supportive", "leading"]
        assert values == expected

    def test_categories(self):
        values = [e.value for e in StakeholderCategory]
        expected = ["sponsor", "customer", "end_user", "regulator", "supplier", "internal", "external"]
        assert values == expected


class TestTeamRoleEnum:
    def test_roles(self):
        values = [e.value for e in TeamRole]
        expected = [
            "project_manager", "scrum_master", "product_owner",
            "developer", "analyst", "tester", "designer", "architect", "other",
        ]
        assert values == expected


class TestTaskEnums:
    def test_statuses(self):
        values = [e.value for e in TaskStatus]
        expected = ["backlog", "todo", "in_progress", "in_review", "done", "blocked"]
        assert values == expected

    def test_priorities(self):
        values = [e.value for e in TaskPriority]
        expected = ["critical", "high", "medium", "low"]
        assert values == expected


class TestRiskEnums:
    def test_categories(self):
        values = [e.value for e in RiskCategory]
        expected = ["technical", "external", "organizational", "project_management"]
        assert values == expected

    def test_probabilities(self):
        values = [e.value for e in RiskProbability]
        expected = ["very_low", "low", "medium", "high", "very_high"]
        assert values == expected

    def test_impacts(self):
        values = [e.value for e in RiskImpact]
        expected = ["very_low", "low", "medium", "high", "very_high"]
        assert values == expected

    def test_statuses(self):
        values = [e.value for e in RiskStatus]
        expected = ["identified", "analyzing", "planned", "active", "resolved", "closed"]
        assert values == expected

    def test_strategies(self):
        values = [e.value for e in RiskStrategy]
        expected = ["avoid", "mitigate", "transfer", "accept", "escalate", "exploit", "enhance", "share"]
        assert values == expected


class TestDeliverableEnums:
    def test_statuses(self):
        values = [e.value for e in DeliverableStatus]
        expected = ["planned", "in_progress", "ready_for_review", "accepted", "rejected"]
        assert values == expected

    def test_quality_levels(self):
        values = [e.value for e in QualityLevel]
        expected = ["not_assessed", "below_standard", "meets_standard", "exceeds_standard"]
        assert values == expected


class TestMeasurementEnums:
    def test_metric_types(self):
        values = [e.value for e in MetricType]
        expected = ["kpi", "leading", "lagging", "outcome"]
        assert values == expected

    def test_domains(self):
        values = [e.value for e in MeasurementDomain]
        expected = ["schedule", "cost", "quality", "scope", "risk", "stakeholder", "team", "value"]
        assert values == expected


class TestChangeRequestEnums:
    def test_statuses(self):
        values = [e.value for e in ChangeStatus]
        expected = ["submitted", "under_review", "approved", "rejected", "implemented", "deferred"]
        assert values == expected

    def test_impacts(self):
        values = [e.value for e in ChangeImpact]
        expected = ["low", "medium", "high", "critical"]
        assert values == expected


class TestModelRelationships:
    def test_project_has_relationships(self):
        p = Project.__mapper__.relationships
        expected_rels = [
            "stakeholders", "team_members", "tasks", "risks",
            "deliverables", "measurements", "change_requests",
        ]
        actual_rels = [r.key for r in p]
        for rel in expected_rels:
            assert rel in actual_rels, f"Missing relationship: {rel}"

    def test_project_cascade_delete(self):
        for rel in Project.__mapper__.relationships:
            if rel.key in ["stakeholders", "team_members", "tasks", "risks",
                           "deliverables", "measurements", "change_requests"]:
                cascade = str(rel.cascade)
                assert "delete" in cascade, f"{rel.key} missing cascade delete"

    def test_task_has_assignee_relationship(self):
        rels = {r.key for r in Task.__mapper__.relationships}
        assert "assignee" in rels
        assert "project" in rels

    def test_risk_has_owner_relationship(self):
        rels = {r.key for r in Risk.__mapper__.relationships}
        assert "owner" in rels
        assert "project" in rels

    def test_change_request_has_reviewer_relationship(self):
        rels = {r.key for r in ChangeRequest.__mapper__.relationships}
        assert "requested_by" in rels
        assert "reviewed_by" in rels
        assert "project" in rels
