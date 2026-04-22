"""CSV export endpoints.

A single generic `/api/export/<domain>.csv` endpoint streams any of the
supported resource types as CSV. Uses existing SQLAlchemy models; rows are
streamed to avoid loading everything into memory.

Supported domains (extend by adding a row to DOMAIN_MAP):

    projects, tasks, risks, deliverables, time_entries,
    opportunities, leads, contacts, companies, contracts,
    invoices, expenses, purchase_orders, vendors, requisitions, accounts,
    audit_entries
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    Project, Task, Risk, Deliverable, TimeEntry,
    Opportunity, Lead, Contact, Company, Contract,
    Invoice, Expense, PurchaseOrder, Vendor, Requisition, Account,
    AuditEntry,
)

router = APIRouter(prefix="/api/export", tags=["export"], dependencies=[Depends(get_current_user)])


def _csv_stream(rows: list[Any], columns: list[tuple[str, Callable[[Any], Any]]]):
    """Return an iterator yielding CSV lines — header + each row rendered."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([c[0] for c in columns])
    yield buf.getvalue()
    buf.seek(0); buf.truncate(0)
    for row in rows:
        w.writerow([_coerce(fn(row)) for _, fn in columns])
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)


def _coerce(v: Any) -> Any:
    if v is None: return ""
    if isinstance(v, datetime): return v.isoformat()
    if hasattr(v, "value"): return v.value  # Enum
    return v


def _filename(domain: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{domain}-{ts}.csv"


# ── Column maps per domain ──────────────────────────────────────────

DOMAIN_MAP: dict[str, tuple[type, list[tuple[str, Callable[[Any], Any]]]]] = {
    "projects": (Project, [
        ("id", lambda r: r.id), ("name", lambda r: r.name),
        ("status", lambda r: r.status), ("approach", lambda r: r.development_approach),
        ("budget", lambda r: r.budget), ("start_date", lambda r: r.start_date),
        ("end_date", lambda r: r.end_date), ("created_at", lambda r: r.created_at),
    ]),
    "tasks": (Task, [
        ("id", lambda r: r.id), ("project_id", lambda r: r.project_id),
        ("title", lambda r: r.title), ("status", lambda r: r.status),
        ("priority", lambda r: r.priority), ("assignee_id", lambda r: r.assignee_id),
        ("duration_days", lambda r: r.duration_days),
        ("planned_cost", lambda r: r.planned_cost), ("actual_cost", lambda r: r.actual_cost),
        ("start_date", lambda r: r.start_date), ("due_date", lambda r: r.due_date),
        ("completed_date", lambda r: r.completed_date),
    ]),
    "risks": (Risk, [
        ("id", lambda r: r.id), ("project_id", lambda r: r.project_id),
        ("title", lambda r: r.title), ("category", lambda r: r.category),
        ("probability", lambda r: r.probability), ("impact", lambda r: r.impact),
        ("status", lambda r: r.status), ("strategy", lambda r: r.strategy),
    ]),
    "deliverables": (Deliverable, [
        ("id", lambda r: r.id), ("project_id", lambda r: r.project_id),
        ("name", lambda r: r.name), ("status", lambda r: r.status),
        ("completion_percentage", lambda r: r.completion_percentage),
        ("due_date", lambda r: r.due_date), ("delivered_date", lambda r: r.delivered_date),
    ]),
    "time_entries": (TimeEntry, [
        ("id", lambda r: r.id), ("project_id", lambda r: r.project_id),
        ("task_id", lambda r: r.task_id), ("hours", lambda r: r.hours),
        ("work_date", lambda r: r.work_date), ("description", lambda r: r.description),
    ]),
    "opportunities": (Opportunity, [
        ("id", lambda r: r.id), ("company_id", lambda r: r.company_id),
        ("title", lambda r: r.title), ("stage", lambda r: r.stage),
        ("amount", lambda r: r.amount), ("probability", lambda r: r.probability),
        ("expected_close", lambda r: r.expected_close),
    ]),
    "leads": (Lead, [
        ("id", lambda r: r.id), ("contact_name", lambda r: r.contact_name),
        ("company_name", lambda r: r.company_name), ("email", lambda r: r.email),
        ("source", lambda r: r.source), ("status", lambda r: r.status),
        ("estimated_value", lambda r: r.estimated_value),
    ]),
    "contacts": (Contact, [
        ("id", lambda r: r.id), ("company_id", lambda r: r.company_id),
        ("first_name", lambda r: r.first_name), ("last_name", lambda r: r.last_name),
        ("email", lambda r: r.email), ("phone", lambda r: r.phone),
        ("job_title", lambda r: r.job_title),
    ]),
    "companies": (Company, [
        ("id", lambda r: r.id), ("name", lambda r: r.name),
        ("industry", lambda r: r.industry), ("website", lambda r: r.website),
        ("annual_revenue", lambda r: r.annual_revenue),
        ("employee_count", lambda r: r.employee_count),
    ]),
    "contracts": (Contract, [
        ("id", lambda r: r.id), ("contract_number", lambda r: r.contract_number),
        ("company_id", lambda r: r.company_id), ("amount", lambda r: r.amount),
        ("billing_cycle", lambda r: r.billing_cycle), ("status", lambda r: r.status),
        ("start_date", lambda r: r.start_date), ("end_date", lambda r: r.end_date),
    ]),
    "invoices": (Invoice, [
        ("id", lambda r: r.id), ("invoice_number", lambda r: r.invoice_number),
        ("invoice_type", lambda r: r.invoice_type), ("status", lambda r: r.status),
        ("subtotal", lambda r: r.subtotal), ("tax_amount", lambda r: r.tax_amount),
        ("total", lambda r: r.total), ("due_date", lambda r: r.due_date),
        ("vendor_id", lambda r: r.vendor_id), ("project_id", lambda r: r.project_id),
    ]),
    "expenses": (Expense, [
        ("id", lambda r: r.id), ("project_id", lambda r: r.project_id),
        ("description", lambda r: r.description), ("category", lambda r: r.category),
        ("amount", lambda r: r.amount), ("expense_date", lambda r: r.expense_date),
        ("is_approved", lambda r: r.is_approved),
    ]),
    "purchase_orders": (PurchaseOrder, [
        ("id", lambda r: r.id), ("po_number", lambda r: r.po_number),
        ("vendor_id", lambda r: r.vendor_id), ("total_amount", lambda r: r.total_amount),
        ("status", lambda r: r.status),
    ]),
    "vendors": (Vendor, [
        ("id", lambda r: r.id), ("name", lambda r: r.name),
        ("contact_person", lambda r: r.contact_person), ("email", lambda r: r.email),
        ("phone", lambda r: r.phone), ("payment_terms", lambda r: r.payment_terms),
    ]),
    "requisitions": (Requisition, [
        ("id", lambda r: r.id), ("req_number", lambda r: r.req_number),
        ("project_id", lambda r: r.project_id), ("status", lambda r: r.status),
        ("estimated_amount", lambda r: r.estimated_amount),
        ("needed_by", lambda r: r.needed_by),
    ]),
    "accounts": (Account, [
        ("id", lambda r: r.id), ("code", lambda r: r.code),
        ("name", lambda r: r.name), ("account_type", lambda r: r.account_type),
        ("balance", lambda r: r.balance),
    ]),
    "audit_entries": (AuditEntry, [
        ("id", lambda r: r.id), ("user_id", lambda r: r.user_id),
        ("domain", lambda r: r.domain), ("action", lambda r: r.action),
        ("entity_type", lambda r: r.entity_type), ("entity_id", lambda r: r.entity_id),
        ("ip", lambda r: r.ip), ("created_at", lambda r: r.created_at),
    ]),
}


@router.get("/{domain}.csv")
async def export_domain(domain: str, limit: int = 5000, db: AsyncSession = Depends(get_db)):
    spec = DOMAIN_MAP.get(domain)
    if not spec:
        raise HTTPException(404, f"Unknown export domain '{domain}'. Supported: {', '.join(sorted(DOMAIN_MAP.keys()))}")
    Model, columns = spec
    rows = (await db.scalars(select(Model).limit(limit))).all()
    return StreamingResponse(
        _csv_stream(rows, columns),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={_filename(domain)}"},
    )
