"""Integration tests for #43 Timesheets + #68 Tags + #67 Batch tracking."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


# ─── #68 Tags ─────────────────────────────────────────────────────────


async def test_tag_create_attach_detach_roundtrip(client):
    # Create
    r = await client.post("/api/tags", json={"name": "urgent", "color": "#ef4444"})
    assert r.status_code == 201, r.text
    tag = r.json()
    tag_id = tag["id"]
    assert tag["name"] == "urgent"

    # Duplicate name rejected
    r2 = await client.post("/api/tags", json={"name": "urgent"})
    assert r2.status_code == 400

    # Attach to a fake entity
    import uuid as _uuid
    fake_entity = str(_uuid.uuid4())
    r = await client.post(f"/api/tags/{tag_id}/attach", json={"entity_type": "invoice", "entity_id": fake_entity})
    assert r.status_code == 201

    # Idempotent attach (already linked)
    r = await client.post(f"/api/tags/{tag_id}/attach", json={"entity_type": "invoice", "entity_id": fake_entity})
    assert r.status_code == 201
    assert r.json().get("already") is True

    # List for entity
    r = await client.get(f"/api/tags/for?entity_type=invoice&entity_id={fake_entity}")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "urgent" in names

    # Detach
    r = await client.delete(f"/api/tags/{tag_id}/detach?entity_type=invoice&entity_id={fake_entity}")
    assert r.status_code == 204

    # Listed for entity is empty again
    r = await client.get(f"/api/tags/for?entity_type=invoice&entity_id={fake_entity}")
    assert r.json() == []


# ─── #43 Timesheets ───────────────────────────────────────────────────


async def test_timesheet_open_week_returns_monday_anchored_sheet(client):
    # No projects/tasks/entries — just verify the create-or-get behaviour
    r = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-22"})  # Wed 2026-04-22
    assert r.status_code == 201, r.text
    sheet = r.json()
    # Monday of that week is 2026-04-20
    assert sheet["week_start"] == "2026-04-20"
    assert sheet["status"] == "draft"
    assert sheet["total_hours"] == 0


async def test_timesheet_idempotent_per_week(client):
    r1 = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-22"})
    r2 = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-23"})  # same Monday
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


async def test_timesheet_submit_empty_is_rejected(client):
    r = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-13"})
    sheet_id = r.json()["id"]
    r = await client.post(f"/api/hr/timesheets/{sheet_id}/submit")
    assert r.status_code == 400  # Cannot submit an empty timesheet


async def test_timesheet_submit_locks_after_attaching_entries(client):
    """Manually attach a TimeEntry inside the week, then submit succeeds and
    the sheet becomes locked."""
    from tests.conftest import async_session_test, _test_user_id
    from app.models.project import Project
    from app.models.task import Task
    from app.models.time_entry import TimeEntry
    from datetime import datetime
    import uuid

    async with async_session_test() as db:
        # Need a Project + Task for the FK
        proj = Project(name="TS Test Proj")
        db.add(proj); await db.commit(); await db.refresh(proj)
        task = Task(project_id=proj.id, title="Some work")
        db.add(task); await db.commit(); await db.refresh(task)
        # Add a time entry inside the week of 2026-04-13 (Mon) → 2026-04-19
        db.add(TimeEntry(
            project_id=proj.id, task_id=task.id, user_id=_test_user_id,
            hours=4.0, work_date=datetime(2026, 4, 14, 10, 0),
            description="dev work",
        ))
        await db.commit()

    r = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-13"})
    sheet = r.json()
    sheet_id = sheet["id"]
    assert sheet["total_hours"] == 4.0  # auto-attached on create
    r = await client.post(f"/api/hr/timesheets/{sheet_id}/submit")
    assert r.status_code == 200
    submitted = r.json()
    assert submitted["status"] == "submitted"
    assert submitted["is_locked"] is True
    # Re-submit fails
    r = await client.post(f"/api/hr/timesheets/{sheet_id}/submit")
    assert r.status_code == 400


async def test_timesheet_decide_approve(client):
    """Approve a submitted timesheet and confirm status flips."""
    from tests.conftest import async_session_test, _test_user_id
    from app.models.project import Project
    from app.models.task import Task
    from app.models.time_entry import TimeEntry
    from datetime import datetime

    async with async_session_test() as db:
        proj = Project(name="TS Approve Proj")
        db.add(proj); await db.commit(); await db.refresh(proj)
        task = Task(project_id=proj.id, title="approve work")
        db.add(task); await db.commit(); await db.refresh(task)
        db.add(TimeEntry(
            project_id=proj.id, task_id=task.id, user_id=_test_user_id,
            hours=8.0, work_date=datetime(2026, 4, 7, 10, 0),
        ))
        await db.commit()

    r = await client.post("/api/hr/timesheets", json={"week_start": "2026-04-06"})  # Mon
    sheet_id = r.json()["id"]
    await client.post(f"/api/hr/timesheets/{sheet_id}/submit")
    r = await client.post(
        f"/api/hr/timesheets/{sheet_id}/decide",
        json={"decision": "approved", "note": "looks good"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert body["decision_note"] == "looks good"
    assert body["is_locked"] is True
