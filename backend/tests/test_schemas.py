import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead
from app.schemas.stakeholder import StakeholderCreate, StakeholderUpdate
from app.schemas.team_member import TeamMemberCreate, TeamMemberUpdate
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.risk import RiskCreate, RiskUpdate
from app.schemas.deliverable import DeliverableCreate, DeliverableUpdate
from app.schemas.measurement import MeasurementCreate, MeasurementUpdate
from app.schemas.change_request import ChangeRequestCreate, ChangeRequestUpdate


class TestProjectSchemas:
    def test_create_minimal(self):
        schema = ProjectCreate(name="Test")
        assert schema.name == "Test"
        assert schema.status == "initiating"
        assert schema.development_approach == "predictive"

    def test_create_full(self):
        schema = ProjectCreate(
            name="Full",
            description="Desc",
            status="planning",
            development_approach="agile",
            delivery_cadence="periodic",
            budget=50000.0,
            vision="Vision",
            objectives="Objectives",
            success_criteria="Criteria",
        )
        assert schema.budget == 50000.0

    def test_create_missing_name(self):
        with pytest.raises(ValidationError):
            ProjectCreate()

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="Bad", status="invented")

    def test_create_invalid_approach(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="Bad", development_approach="waterfall2")

    def test_update_all_optional(self):
        schema = ProjectUpdate()
        assert schema.name is None
        assert schema.status is None

    def test_update_partial(self):
        schema = ProjectUpdate(name="New Name", budget=999.0)
        assert schema.name == "New Name"
        assert schema.budget == 999.0
        assert schema.status is None


class TestStakeholderSchemas:
    def test_create_minimal(self):
        schema = StakeholderCreate(project_id=uuid4(), name="SH")
        assert schema.engagement_level == "neutral"
        assert schema.desired_engagement == "supportive"

    def test_create_all_engagement_levels(self):
        for level in ["unaware", "resistant", "neutral", "supportive", "leading"]:
            schema = StakeholderCreate(project_id=uuid4(), name="SH", engagement_level=level)
            assert schema.engagement_level == level

    def test_create_invalid_category(self):
        with pytest.raises(ValidationError):
            StakeholderCreate(project_id=uuid4(), name="SH", category="alien")

    def test_create_missing_name(self):
        with pytest.raises(ValidationError):
            StakeholderCreate(project_id=uuid4())

    def test_update_all_optional(self):
        schema = StakeholderUpdate()
        assert schema.name is None


class TestTeamMemberSchemas:
    def test_create_defaults(self):
        schema = TeamMemberCreate(project_id=uuid4(), name="TM")
        assert schema.role == "developer"
        assert schema.availability == 100.0

    def test_create_all_roles(self):
        roles = ["project_manager", "scrum_master", "product_owner", "developer",
                 "analyst", "tester", "designer", "architect", "other"]
        for role in roles:
            schema = TeamMemberCreate(project_id=uuid4(), name="TM", role=role)
            assert schema.role == role

    def test_create_invalid_role(self):
        with pytest.raises(ValidationError):
            TeamMemberCreate(project_id=uuid4(), name="TM", role="ceo")


class TestTaskSchemas:
    def test_create_defaults(self):
        schema = TaskCreate(project_id=uuid4(), title="Task")
        assert schema.status == "backlog"
        assert schema.priority == "medium"
        assert schema.story_points is None
        assert schema.assignee_id is None

    def test_create_all_statuses(self):
        for s in ["backlog", "todo", "in_progress", "in_review", "done", "blocked"]:
            schema = TaskCreate(project_id=uuid4(), title="T", status=s)
            assert schema.status == s

    def test_create_all_priorities(self):
        for p in ["critical", "high", "medium", "low"]:
            schema = TaskCreate(project_id=uuid4(), title="T", priority=p)
            assert schema.priority == p

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            TaskCreate(project_id=uuid4(), title="T", status="canceled")

    def test_create_invalid_priority(self):
        with pytest.raises(ValidationError):
            TaskCreate(project_id=uuid4(), title="T", priority="super")

    def test_create_missing_title(self):
        with pytest.raises(ValidationError):
            TaskCreate(project_id=uuid4())

    def test_update_with_assignee(self):
        aid = uuid4()
        schema = TaskUpdate(assignee_id=aid)
        assert schema.assignee_id == aid


class TestRiskSchemas:
    def test_create_defaults(self):
        schema = RiskCreate(project_id=uuid4(), title="Risk")
        assert schema.category == "technical"
        assert schema.probability == "medium"
        assert schema.impact == "medium"
        assert schema.status == "identified"
        assert schema.strategy == "mitigate"

    def test_create_all_categories(self):
        for c in ["technical", "external", "organizational", "project_management"]:
            schema = RiskCreate(project_id=uuid4(), title="R", category=c)
            assert schema.category == c

    def test_create_all_strategies(self):
        for s in ["avoid", "mitigate", "transfer", "accept", "escalate", "exploit", "enhance", "share"]:
            schema = RiskCreate(project_id=uuid4(), title="R", strategy=s)
            assert schema.strategy == s

    def test_create_all_probabilities(self):
        for p in ["very_low", "low", "medium", "high", "very_high"]:
            schema = RiskCreate(project_id=uuid4(), title="R", probability=p)
            assert schema.probability == p

    def test_create_invalid_category(self):
        with pytest.raises(ValidationError):
            RiskCreate(project_id=uuid4(), title="R", category="financial")

    def test_create_invalid_strategy(self):
        with pytest.raises(ValidationError):
            RiskCreate(project_id=uuid4(), title="R", strategy="hope")


class TestDeliverableSchemas:
    def test_create_defaults(self):
        schema = DeliverableCreate(project_id=uuid4(), name="Del")
        assert schema.status == "planned"
        assert schema.quality_level == "not_assessed"
        assert schema.completion_percentage == 0.0

    def test_create_all_statuses(self):
        for s in ["planned", "in_progress", "ready_for_review", "accepted", "rejected"]:
            schema = DeliverableCreate(project_id=uuid4(), name="D", status=s)
            assert schema.status == s

    def test_create_all_quality_levels(self):
        for q in ["not_assessed", "below_standard", "meets_standard", "exceeds_standard"]:
            schema = DeliverableCreate(project_id=uuid4(), name="D", quality_level=q)
            assert schema.quality_level == q

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            DeliverableCreate(project_id=uuid4(), name="D", status="shipped")


class TestMeasurementSchemas:
    def test_create_defaults(self):
        schema = MeasurementCreate(project_id=uuid4(), name="M")
        assert schema.metric_type == "kpi"
        assert schema.domain == "value"

    def test_create_all_metric_types(self):
        for mt in ["kpi", "leading", "lagging", "outcome"]:
            schema = MeasurementCreate(project_id=uuid4(), name="M", metric_type=mt)
            assert schema.metric_type == mt

    def test_create_all_domains(self):
        for d in ["schedule", "cost", "quality", "scope", "risk", "stakeholder", "team", "value"]:
            schema = MeasurementCreate(project_id=uuid4(), name="M", domain=d)
            assert schema.domain == d

    def test_create_invalid_type(self):
        with pytest.raises(ValidationError):
            MeasurementCreate(project_id=uuid4(), name="M", metric_type="vanity")

    def test_create_with_thresholds(self):
        schema = MeasurementCreate(
            project_id=uuid4(), name="M",
            threshold_red=0.7, threshold_yellow=0.85, threshold_green=1.0,
        )
        assert schema.threshold_red == 0.7


class TestChangeRequestSchemas:
    def test_create_defaults(self):
        schema = ChangeRequestCreate(project_id=uuid4(), title="CR")
        assert schema.status == "submitted"
        assert schema.impact == "medium"

    def test_create_all_statuses(self):
        for s in ["submitted", "under_review", "approved", "rejected", "implemented", "deferred"]:
            schema = ChangeRequestCreate(project_id=uuid4(), title="CR", status=s)
            assert schema.status == s

    def test_create_all_impacts(self):
        for i in ["low", "medium", "high", "critical"]:
            schema = ChangeRequestCreate(project_id=uuid4(), title="CR", impact=i)
            assert schema.impact == i

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            ChangeRequestCreate(project_id=uuid4(), title="CR", status="magic")

    def test_create_invalid_impact(self):
        with pytest.raises(ValidationError):
            ChangeRequestCreate(project_id=uuid4(), title="CR", impact="nuclear")

    def test_update_reviewer(self):
        rid = uuid4()
        schema = ChangeRequestUpdate(reviewed_by_id=rid, status="under_review")
        assert schema.reviewed_by_id == rid
        assert schema.status == "under_review"
