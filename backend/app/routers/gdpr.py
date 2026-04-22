"""GDPR — per-user data export (Right to Access) and deletion (Right to Erasure).

Export packages every row tied to the calling user across known tables into a
single ZIP of JSON files. Deletion is a *soft* delete that anonymizes PII and
detaches the auth side, but preserves audit-log integrity (foreign keys to
`users.id` would otherwise cascade and destroy history).
"""

import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.comment import Comment
from app.models.activity_log import ActivityLog
from app.models.time_entry import TimeEntry
from app.models.team_member import TeamMember
from app.models.cross import AuditEntry, ApprovalRequest
from app.models.acl import UserPermission, ProjectMember
from app.models.hr import Employee, LeaveRequest

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"], dependencies=[Depends(get_current_user)])

logger = logging.getLogger(__name__)


def _serialise(obj: Any) -> Any:
    """Best-effort JSON serialiser for SQLAlchemy rows."""
    out: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if val is None:
            out[col.name] = None
        elif isinstance(val, (datetime,)):
            out[col.name] = val.isoformat()
        elif hasattr(val, "value"):  # enum
            out[col.name] = val.value
        elif hasattr(val, "hex"):  # uuid
            out[col.name] = str(val)
        else:
            out[col.name] = val
    return out


async def _collect_user_data(db: AsyncSession, user: User) -> dict[str, list]:
    """Gather every row that belongs to this user across tracked tables."""
    bundle: dict[str, list] = {}

    bundle["user"] = [_serialise(user)]

    # Tables with a `user_id` column we know about
    for label, model, col in [
        ("notifications", Notification, Notification.user_id),
        ("comments", Comment, Comment.user_id),
        ("activity_log", ActivityLog, ActivityLog.user_id),
        ("time_entries", TimeEntry, TimeEntry.user_id),
        ("team_members", TeamMember, TeamMember.user_id),
        ("audit_entries", AuditEntry, AuditEntry.user_id),
        ("user_permissions", UserPermission, UserPermission.user_id),
        ("project_members", ProjectMember, ProjectMember.user_id),
        ("hr_employees", Employee, Employee.user_id),
    ]:
        try:
            r = await db.execute(select(model).where(col == user.id))
            bundle[label] = [_serialise(row) for row in r.scalars().all()]
        except Exception:
            logger.warning("GDPR export: failed for %s", label, exc_info=True)
            bundle[label] = []

    # Approval requests where they're requester or approver
    try:
        r = await db.execute(
            select(ApprovalRequest).where(
                (ApprovalRequest.requester_id == user.id) | (ApprovalRequest.approver_id == user.id)
            )
        )
        bundle["approvals"] = [_serialise(row) for row in r.scalars().all()]
    except Exception:
        bundle["approvals"] = []

    # Leave requests through the employee link
    try:
        emp_r = await db.execute(select(Employee).where(Employee.user_id == user.id))
        emp = emp_r.scalar_one_or_none()
        if emp:
            r = await db.execute(select(LeaveRequest).where(LeaveRequest.employee_id == emp.id))
            bundle["hr_leave_requests"] = [_serialise(row) for row in r.scalars().all()]
        else:
            bundle["hr_leave_requests"] = []
    except Exception:
        bundle["hr_leave_requests"] = []

    return bundle


@router.get("/export")
async def export_my_data(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Right to Access: returns a ZIP containing one JSON file per table the user appears in."""
    bundle = await _collect_user_data(db, current_user)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "_index.json",
            json.dumps(
                {
                    "user_id": str(current_user.id),
                    "email": current_user.email,
                    "exported_at": datetime.utcnow().isoformat(),
                    "tables": {label: len(rows) for label, rows in bundle.items()},
                },
                indent=2,
                default=str,
            ),
        )
        for label, rows in bundle.items():
            zf.writestr(f"{label}.json", json.dumps(rows, indent=2, default=str))
    buf.seek(0)

    filename = f"gdpr-export-{str(current_user.id)[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/me", status_code=200)
async def delete_my_account(
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Right to Erasure: soft-delete + PII anonymization. Audit history kept via FK retention."""
    if not confirm:
        raise HTTPException(400, "Pass ?confirm=true to actually delete your account")
    redacted_email = f"redacted-{str(current_user.id)[:8]}@deleted.local"
    current_user.email = redacted_email
    current_user.name = "Deleted user"
    current_user.is_active = False
    # Force a password the user cannot use again (dummy hash)
    current_user.hashed_password = "!DELETED!"
    await db.commit()
    return {"id": str(current_user.id), "redacted_email": redacted_email, "ok": True}


@router.get("/admin/exports", dependencies=[Depends(require_permission("admin.user.manage"))])
async def admin_recent_exports(db: AsyncSession = Depends(get_db)):
    """Admin view — recent users who have requested an export (logged via audit)."""
    r = await db.execute(
        select(AuditEntry).where(AuditEntry.action == "gdpr_export").order_by(AuditEntry.created_at.desc()).limit(50)
    )
    return [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in r.scalars().all()
    ]
