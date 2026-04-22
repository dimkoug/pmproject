"""HR — employees, leave requests, attendance."""

from datetime import datetime, date, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import apply_field_mask, get_field_mask, require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.hr import (
    Attendance, AttendanceSource,
    Employee, LeaveRequest, LeaveStatus, LeaveType,
)
from app.models.time_entry import TimeEntry, Timesheet, TimesheetStatus
from app.models.user import User

router = APIRouter(prefix="/api/hr", tags=["hr"], dependencies=[Depends(get_current_user)])


# ── Employees ──────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    user_id: UUID | None = None
    employee_number: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    job_title: str | None = None
    hire_date: str | None = None
    manager_id: UUID | None = None
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    job_title: str | None = None
    manager_id: UUID | None = None
    user_id: UUID | None = None
    is_active: bool | None = None
    termination_date: str | None = None
    notes: str | None = None


def _employee_dict(e: Employee) -> dict:
    return {
        "id": str(e.id),
        "user_id": str(e.user_id) if e.user_id else None,
        "employee_number": e.employee_number,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "full_name": f"{e.first_name} {e.last_name}".strip(),
        "email": e.email,
        "phone": e.phone,
        "department": e.department,
        "job_title": e.job_title,
        "hire_date": e.hire_date.isoformat() if e.hire_date else None,
        "termination_date": e.termination_date.isoformat() if e.termination_date else None,
        "manager_id": str(e.manager_id) if e.manager_id else None,
        "is_active": e.is_active,
        "notes": e.notes,
    }


@router.get("/employees", dependencies=[Depends(require_permission("hr.employee.view"))])
async def list_employees(
    request: Request,
    department: str | None = None,
    active: bool | None = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Employee).order_by(Employee.last_name, Employee.first_name).limit(500)
    if department:
        q = q.where(Employee.department == department)
    if active is not None:
        q = q.where(Employee.is_active == active)
    r = await db.execute(q)
    masked = await get_field_mask(db, current_user, "employee", request=request)
    return [apply_field_mask(_employee_dict(e), masked) for e in r.scalars().all()]


@router.get("/employees/me")
async def get_my_employee(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Employee).where(Employee.user_id == current_user.id))
    e = r.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "No employee record linked to your user")
    return _employee_dict(e)


@router.get("/employees/{employee_id}", dependencies=[Depends(require_permission("hr.employee.view"))])
async def get_employee(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    e = await db.get(Employee, employee_id)
    if not e:
        raise HTTPException(404, "Employee not found")
    return _employee_dict(e)


@router.post("/employees", status_code=201, dependencies=[Depends(require_permission("hr.employee.manage"))])
async def create_employee(p: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Employee).where(Employee.employee_number == p.employee_number))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Employee number '{p.employee_number}' already exists")
    e = Employee(
        user_id=p.user_id,
        employee_number=p.employee_number,
        first_name=p.first_name,
        last_name=p.last_name,
        email=p.email,
        phone=p.phone,
        department=p.department,
        job_title=p.job_title,
        hire_date=date.fromisoformat(p.hire_date) if p.hire_date else None,
        manager_id=p.manager_id,
        notes=p.notes,
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return _employee_dict(e)


@router.patch("/employees/{employee_id}", dependencies=[Depends(require_permission("hr.employee.manage"))])
async def update_employee(employee_id: UUID, p: EmployeeUpdate, db: AsyncSession = Depends(get_db)):
    e = await db.get(Employee, employee_id)
    if not e:
        raise HTTPException(404, "Employee not found")
    data = p.model_dump(exclude_unset=True)
    if "termination_date" in data and data["termination_date"]:
        data["termination_date"] = date.fromisoformat(data["termination_date"])
    for k, v in data.items():
        setattr(e, k, v)
    await db.commit()
    return _employee_dict(e)


@router.delete("/employees/{employee_id}", status_code=204, dependencies=[Depends(require_permission("hr.employee.manage"))])
async def delete_employee(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    e = await db.get(Employee, employee_id)
    if not e:
        raise HTTPException(404, "Employee not found")
    await db.delete(e)
    await db.commit()


# ── Leave Requests ─────────────────────────────────────────────────

class LeaveCreate(BaseModel):
    employee_id: UUID
    leave_type: LeaveType = LeaveType.VACATION
    start_date: str
    end_date: str
    reason: str | None = None


class LeaveDecide(BaseModel):
    decision: LeaveStatus  # APPROVED or REJECTED
    note: str | None = None


def _leave_dict(lr: LeaveRequest, emp: Employee | None = None) -> dict:
    return {
        "id": str(lr.id),
        "employee_id": str(lr.employee_id),
        "employee_name": f"{emp.first_name} {emp.last_name}".strip() if emp else None,
        "leave_type": lr.leave_type.value,
        "start_date": lr.start_date.isoformat() if lr.start_date else None,
        "end_date": lr.end_date.isoformat() if lr.end_date else None,
        "days": lr.days,
        "reason": lr.reason,
        "status": lr.status.value,
        "approver_id": str(lr.approver_id) if lr.approver_id else None,
        "decided_at": lr.decided_at.isoformat() if lr.decided_at else None,
        "decision_note": lr.decision_note,
        "created_at": lr.created_at.isoformat() if lr.created_at else None,
    }


@router.get("/leave-requests", dependencies=[Depends(require_permission("hr.leave.view"))])
async def list_leaves(
    status: str | None = None,
    employee_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(LeaveRequest).order_by(LeaveRequest.created_at.desc()).limit(500)
    if status:
        q = q.where(LeaveRequest.status == LeaveStatus(status))
    if employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    r = await db.execute(q)
    leaves = r.scalars().all()
    # Resolve employee names in one batch
    emp_ids = {lr.employee_id for lr in leaves}
    emps = {}
    if emp_ids:
        er = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        emps = {e.id: e for e in er.scalars().all()}
    return [_leave_dict(lr, emps.get(lr.employee_id)) for lr in leaves]


@router.post("/leave-requests", status_code=201, dependencies=[Depends(require_permission("hr.leave.request"))])
async def create_leave(p: LeaveCreate, db: AsyncSession = Depends(get_db)):
    start = date.fromisoformat(p.start_date)
    end = date.fromisoformat(p.end_date)
    if end < start:
        raise HTTPException(400, "end_date must be on or after start_date")
    days = (end - start).days + 1
    lr = LeaveRequest(
        employee_id=p.employee_id,
        leave_type=p.leave_type,
        start_date=start,
        end_date=end,
        days=days,
        reason=p.reason,
    )
    db.add(lr)
    await db.commit()
    await db.refresh(lr)
    return _leave_dict(lr)


@router.post("/leave-requests/{leave_id}/decide", dependencies=[Depends(require_permission("hr.leave.approve"))])
async def decide_leave(
    leave_id: UUID,
    p: LeaveDecide,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lr = await db.get(LeaveRequest, leave_id)
    if not lr:
        raise HTTPException(404, "Leave request not found")
    if lr.status != LeaveStatus.PENDING:
        raise HTTPException(400, f"Already {lr.status.value} — cannot change")
    if p.decision not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
        raise HTTPException(400, "decision must be approved or rejected")
    lr.status = p.decision
    lr.approver_id = current_user.id
    lr.decided_at = datetime.now(timezone.utc)
    lr.decision_note = p.note
    await db.commit()
    return _leave_dict(lr)


# ── Attendance ─────────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    employee_id: UUID
    work_date: str
    check_in: str | None = None
    check_out: str | None = None
    source: AttendanceSource = AttendanceSource.MANUAL
    notes: str | None = None


def _attendance_dict(a: Attendance, emp: Employee | None = None) -> dict:
    return {
        "id": str(a.id),
        "employee_id": str(a.employee_id),
        "employee_name": f"{emp.first_name} {emp.last_name}".strip() if emp else None,
        "work_date": a.work_date.isoformat() if a.work_date else None,
        "check_in": a.check_in.isoformat() if a.check_in else None,
        "check_out": a.check_out.isoformat() if a.check_out else None,
        "hours_worked": a.hours_worked,
        "source": a.source.value if a.source else None,
        "notes": a.notes,
    }


def _hours_between(check_in: datetime | None, check_out: datetime | None) -> float | None:
    if not check_in or not check_out:
        return None
    delta = check_out - check_in
    return round(delta.total_seconds() / 3600.0, 3)


@router.get("/attendance", dependencies=[Depends(require_permission("hr.attendance.view"))])
async def list_attendance(
    employee_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Attendance).order_by(Attendance.work_date.desc(), Attendance.check_in.desc()).limit(500)
    if employee_id:
        q = q.where(Attendance.employee_id == employee_id)
    if date_from:
        q = q.where(Attendance.work_date >= date.fromisoformat(date_from))
    if date_to:
        q = q.where(Attendance.work_date <= date.fromisoformat(date_to))
    r = await db.execute(q)
    rows = r.scalars().all()
    emp_ids = {a.employee_id for a in rows}
    emps = {}
    if emp_ids:
        er = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        emps = {e.id: e for e in er.scalars().all()}
    return [_attendance_dict(a, emps.get(a.employee_id)) for a in rows]


@router.post("/attendance", status_code=201, dependencies=[Depends(require_permission("hr.attendance.manage"))])
async def create_attendance(p: AttendanceCreate, db: AsyncSession = Depends(get_db)):
    ci = datetime.fromisoformat(p.check_in) if p.check_in else None
    co = datetime.fromisoformat(p.check_out) if p.check_out else None
    a = Attendance(
        employee_id=p.employee_id,
        work_date=date.fromisoformat(p.work_date),
        check_in=ci,
        check_out=co,
        hours_worked=_hours_between(ci, co),
        source=p.source,
        notes=p.notes,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _attendance_dict(a)


@router.post("/attendance/check-in")
async def check_in(
    source: AttendanceSource = AttendanceSource.WEB,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    er = await db.execute(select(Employee).where(Employee.user_id == current_user.id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "No employee record linked to your user")
    today = date.today()
    # If there's already an open record today, return it (idempotent)
    existing = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == emp.id,
            Attendance.work_date == today,
            Attendance.check_out.is_(None),
        )
    )
    a = existing.scalar_one_or_none()
    if a:
        return _attendance_dict(a, emp)
    a = Attendance(
        employee_id=emp.id,
        work_date=today,
        check_in=datetime.now(timezone.utc),
        source=source,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _attendance_dict(a, emp)


@router.post("/attendance/check-out")
async def check_out(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    er = await db.execute(select(Employee).where(Employee.user_id == current_user.id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "No employee record linked to your user")
    today = date.today()
    existing = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == emp.id,
            Attendance.work_date == today,
            Attendance.check_out.is_(None),
        ).order_by(Attendance.check_in.desc())
    )
    a = existing.scalars().first()
    if not a:
        raise HTTPException(400, "No open check-in for today — call /attendance/check-in first")
    a.check_out = datetime.now(timezone.utc)
    a.hours_worked = _hours_between(a.check_in, a.check_out)
    await db.commit()
    return _attendance_dict(a, emp)


# ── Dashboard ──────────────────────────────────────────────────────

@router.get("/dashboard")
async def hr_dashboard(db: AsyncSession = Depends(get_db)):
    today = date.today()
    week_ago = today - timedelta(days=7)
    active_emp = (await db.execute(
        select(func.count()).select_from(Employee).where(Employee.is_active == True)  # noqa: E712
    )).scalar() or 0
    pending_leave = (await db.execute(
        select(func.count()).select_from(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
    )).scalar() or 0
    today_checkins = (await db.execute(
        select(func.count()).select_from(Attendance).where(Attendance.work_date == today)
    )).scalar() or 0
    on_leave_today = (await db.execute(
        select(func.count()).select_from(LeaveRequest).where(
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
    )).scalar() or 0
    week_attendance = (await db.execute(
        select(func.coalesce(func.sum(Attendance.hours_worked), 0.0)).select_from(Attendance).where(
            Attendance.work_date >= week_ago, Attendance.hours_worked.is_not(None),
        )
    )).scalar() or 0.0
    return {
        "active_employees": int(active_emp),
        "pending_leave": int(pending_leave),
        "today_checkins": int(today_checkins),
        "on_leave_today": int(on_leave_today),
        "hours_logged_7d": round(float(week_attendance), 2),
    }


# ── Timesheets (#43) ───────────────────────────────────────────────

def _week_start(d: date) -> date:
    """Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


def _timesheet_dict(t: Timesheet, user_name: str | None = None) -> dict:
    return {
        "id": str(t.id),
        "user_id": str(t.user_id),
        "user_name": user_name,
        "week_start": t.week_start.isoformat() if t.week_start else None,
        "status": t.status.value,
        "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
        "approver_id": str(t.approver_id) if t.approver_id else None,
        "decided_at": t.decided_at.isoformat() if t.decided_at else None,
        "decision_note": t.decision_note,
        "total_hours": t.total_hours,
        "is_locked": t.status in (TimesheetStatus.SUBMITTED, TimesheetStatus.APPROVED),
    }


async def _get_or_create_timesheet(db: AsyncSession, user_id: UUID, week_start_d: date) -> Timesheet:
    existing = await db.execute(
        select(Timesheet).where(Timesheet.user_id == user_id, Timesheet.week_start == week_start_d)
    )
    ts = existing.scalar_one_or_none()
    if ts:
        return ts
    ts = Timesheet(user_id=user_id, week_start=week_start_d, status=TimesheetStatus.DRAFT)
    db.add(ts)
    await db.flush()
    return ts


async def _attach_entries_to_timesheet(db: AsyncSession, ts: Timesheet) -> float:
    """Link all of the user's entries within [week_start, week_start+7) to this timesheet,
    return the total hours."""
    week_end = ts.week_start + timedelta(days=7)
    entries_q = await db.execute(
        select(TimeEntry).where(
            TimeEntry.user_id == ts.user_id,
            TimeEntry.work_date >= datetime.combine(ts.week_start, datetime.min.time()),
            TimeEntry.work_date < datetime.combine(week_end, datetime.min.time()),
        )
    )
    entries = entries_q.scalars().all()
    total = 0.0
    for e in entries:
        if e.timesheet_id is None:
            e.timesheet_id = ts.id
        if e.timesheet_id == ts.id:
            total += e.hours or 0
    ts.total_hours = round(total, 2)
    return ts.total_hours


@router.get("/timesheets/me")
async def my_timesheets(
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(Timesheet).where(Timesheet.user_id == current_user.id).order_by(Timesheet.week_start.desc()).limit(limit)
    )
    return [_timesheet_dict(t, current_user.name) for t in r.scalars().all()]


class TimesheetCreate(BaseModel):
    week_start: str  # YYYY-MM-DD; will be coerced to Monday of that week


@router.post("/timesheets", status_code=201)
async def create_or_get_timesheet(
    p: TimesheetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week = _week_start(date.fromisoformat(p.week_start))
    ts = await _get_or_create_timesheet(db, current_user.id, week)
    await _attach_entries_to_timesheet(db, ts)
    await db.commit()
    return _timesheet_dict(ts, current_user.name)


@router.post("/timesheets/{timesheet_id}/submit", dependencies=[Depends(require_permission("hr.timesheet.submit"))])
async def submit_timesheet(
    timesheet_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ts = await db.get(Timesheet, timesheet_id)
    if not ts:
        raise HTTPException(404, "Timesheet not found")
    if ts.user_id != current_user.id:
        raise HTTPException(403, "Can only submit your own timesheet")
    if ts.status != TimesheetStatus.DRAFT:
        raise HTTPException(400, f"Already {ts.status.value} — cannot submit")
    await _attach_entries_to_timesheet(db, ts)
    if ts.total_hours <= 0:
        raise HTTPException(400, "Cannot submit an empty timesheet — log time entries first")
    ts.status = TimesheetStatus.SUBMITTED
    ts.submitted_at = datetime.now(timezone.utc)
    await db.commit()
    return _timesheet_dict(ts, current_user.name)


@router.get("/timesheets/inbox", dependencies=[Depends(require_permission("hr.timesheet.approve"))])
async def approval_inbox(
    status: str | None = Query("submitted"),
    db: AsyncSession = Depends(get_db),
):
    q = select(Timesheet).order_by(Timesheet.submitted_at.desc().nulls_last(), Timesheet.week_start.desc()).limit(200)
    if status:
        q = q.where(Timesheet.status == TimesheetStatus(status))
    r = await db.execute(q)
    rows = r.scalars().all()
    user_ids = {t.user_id for t in rows}
    users = {}
    if user_ids:
        ur = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = {u.id: u for u in ur.scalars().all()}
    return [_timesheet_dict(t, users.get(t.user_id).name if users.get(t.user_id) else None) for t in rows]


class TimesheetDecide(BaseModel):
    decision: TimesheetStatus  # APPROVED or REJECTED
    note: str | None = None


@router.post("/timesheets/{timesheet_id}/decide", dependencies=[Depends(require_permission("hr.timesheet.approve"))])
async def decide_timesheet(
    timesheet_id: UUID,
    p: TimesheetDecide,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ts = await db.get(Timesheet, timesheet_id)
    if not ts:
        raise HTTPException(404, "Timesheet not found")
    if ts.status != TimesheetStatus.SUBMITTED:
        raise HTTPException(400, f"Can only decide submitted timesheets, this one is {ts.status.value}")
    if p.decision not in (TimesheetStatus.APPROVED, TimesheetStatus.REJECTED):
        raise HTTPException(400, "decision must be approved or rejected")
    ts.status = p.decision
    ts.approver_id = current_user.id
    ts.decided_at = datetime.now(timezone.utc)
    ts.decision_note = p.note
    await db.commit()
    return _timesheet_dict(ts)
