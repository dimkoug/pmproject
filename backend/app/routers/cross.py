"""Cross-cutting: unified customer timeline, approval workflow, webhooks, API keys."""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.cross import (
    ApprovalRequest, ApprovalStatus, ApprovalTargetType,
    Webhook, WebhookDelivery, ApiKey,
    AuditEntry, ScheduledReport, ScheduledReportRun, ReportFrequency,
    Dashboard, DashboardWidget, SsoProvider, SsoProviderType,
    Workspace, WorkspaceMember,
)
from app.models.crm import Company, Contact, Interaction, Opportunity, Quote
from app.models.dms import Document, EntityLink, EntityType
from app.models.erp import Expense, Invoice, PurchaseOrder
from app.models.user import User

router = APIRouter(prefix="/api", tags=["cross"], dependencies=[Depends(get_current_user)])


# ── Unified Customer Timeline ───────────────────────────────────────

@router.get("/timeline/company/{company_id}")
async def company_timeline(company_id: UUID, db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company: raise HTTPException(404, "Company not found")

    contact_ids = [c.id for c in (await db.execute(select(Contact).where(Contact.company_id == company_id))).scalars().all()]
    events: list[dict] = []

    # Interactions
    if contact_ids:
        ints = (await db.execute(select(Interaction).where(Interaction.contact_id.in_(contact_ids)))).scalars().all()
        for i in ints:
            events.append({"type": "interaction", "subtype": i.interaction_type.value,
                           "date": i.interaction_date.isoformat() if i.interaction_date else None,
                           "title": i.subject, "detail": i.body, "id": str(i.id)})

    # Opportunities
    opps = (await db.execute(select(Opportunity).where(Opportunity.company_id == company_id))).scalars().all()
    for o in opps:
        events.append({"type": "opportunity", "subtype": o.stage.value,
                       "date": o.created_at.isoformat() if o.created_at else None,
                       "title": o.title, "detail": f"${o.amount or 0} @ {o.stage.value}", "id": str(o.id)})

    # Quotes
    quotes = (await db.execute(select(Quote).where(Quote.company_id == company_id))).scalars().all()
    for q in quotes:
        events.append({"type": "quote", "subtype": q.status.value,
                       "date": q.created_at.isoformat() if q.created_at else None,
                       "title": f"Quote {q.quote_number}", "detail": f"${q.total}", "id": str(q.id)})

    # Linked documents — batch-load to avoid N+1 db.get() per link
    doc_links = (await db.execute(select(EntityLink).where(EntityLink.entity_type == EntityType.COMPANY, EntityLink.entity_id == company_id))).scalars().all()
    if doc_links:
        doc_ids = {l.document_id for l in doc_links}
        docs = (await db.execute(select(Document).where(Document.id.in_(doc_ids)))).scalars().all()
        for d in docs:
            events.append({"type": "document", "subtype": d.status.value,
                           "date": d.created_at.isoformat() if d.created_at else None,
                           "title": d.title, "detail": d.description, "id": str(d.id)})

    events.sort(key=lambda e: e["date"] or "", reverse=True)
    return {"company": {"id": str(company.id), "name": company.name},
            "contact_count": len(contact_ids), "events": events}


# ── Approval Workflow ───────────────────────────────────────────────

class ApprovalRequestCreate(BaseModel):
    target_type: ApprovalTargetType; target_id: UUID
    approver_id: UUID | None = None; threshold_amount: float | None = None
    note: str | None = None

class ApprovalDecision(BaseModel):
    decision: str  # "approved" | "rejected"
    note: str | None = None

@router.get("/approvals")
async def list_approvals(status: str | None = None, target_type: ApprovalTargetType | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(200)
    if status: q = q.where(ApprovalRequest.status == ApprovalStatus(status))
    if target_type: q = q.where(ApprovalRequest.target_type == target_type)
    result = await db.execute(q)
    return [{"id": str(a.id), "target_type": a.target_type.value, "target_id": str(a.target_id),
             "status": a.status.value, "threshold_amount": a.threshold_amount, "note": a.note,
             "decided_at": a.decided_at.isoformat() if a.decided_at else None,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in result.scalars().all()]

@router.post("/approvals", status_code=201)
async def create_approval(p: ApprovalRequestCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = ApprovalRequest(target_type=p.target_type, target_id=p.target_id, approver_id=p.approver_id,
                        threshold_amount=p.threshold_amount, note=p.note, requester_id=current_user.id)
    db.add(a); await db.commit(); await db.refresh(a)
    return {"id": str(a.id), "status": a.status.value}

async def _apply_decision_side_effects(a: ApprovalRequest, db: AsyncSession):
    """When an approval is granted, update the target entity."""
    if a.status != ApprovalStatus.APPROVED: return
    if a.target_type == ApprovalTargetType.EXPENSE:
        e = await db.get(Expense, a.target_id)
        if e: e.is_approved = True
    elif a.target_type == ApprovalTargetType.PO:
        from app.models.erp import POStatus
        po = await db.get(PurchaseOrder, a.target_id)
        if po and po.status.value == "submitted": po.status = POStatus.APPROVED
    elif a.target_type == ApprovalTargetType.DOCUMENT:
        from app.models.dms import DocumentStatus
        d = await db.get(Document, a.target_id)
        if d: d.status = DocumentStatus.APPROVED

@router.post("/approvals/{approval_id}/decide", dependencies=[Depends(require_permission("admin.approval.decide"))])
async def decide_approval(approval_id: UUID, p: ApprovalDecision, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = await db.get(ApprovalRequest, approval_id)
    if not a: raise HTTPException(404, "Approval not found")
    if a.status != ApprovalStatus.PENDING: raise HTTPException(400, f"Already {a.status.value}")
    a.status = ApprovalStatus(p.decision)
    a.note = p.note or a.note
    a.approver_id = current_user.id
    a.decided_at = datetime.utcnow()
    await _apply_decision_side_effects(a, db)
    await db.commit()
    return {"id": str(a.id), "status": a.status.value}


# ── Webhooks ────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    name: str; url: str; events: str = ""; secret: str | None = None

@router.get("/webhooks")
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    return [{"id": str(w.id), "name": w.name, "url": w.url, "events": w.events, "is_active": w.is_active} for w in result.scalars().all()]

@router.post("/webhooks", status_code=201, dependencies=[Depends(require_permission("admin.webhook.manage"))])
async def create_webhook(p: WebhookCreate, db: AsyncSession = Depends(get_db)):
    w = Webhook(name=p.name, url=p.url, events=p.events, secret=p.secret or secrets.token_urlsafe(24))
    db.add(w); await db.commit(); await db.refresh(w)
    return {"id": str(w.id), "secret": w.secret}

@router.delete("/webhooks/{hook_id}", status_code=204, dependencies=[Depends(require_permission("admin.webhook.manage"))])
async def delete_webhook(hook_id: UUID, db: AsyncSession = Depends(get_db)):
    w = await db.get(Webhook, hook_id)
    if not w: raise HTTPException(404, "Not found")
    await db.delete(w); await db.commit()

class WebhookTest(BaseModel):
    event: str = "test.ping"; payload: dict = {}

@router.post("/webhooks/{hook_id}/test", dependencies=[Depends(require_permission("admin.webhook.manage"))])
async def test_webhook(hook_id: UUID, p: WebhookTest, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    w = await db.get(Webhook, hook_id)
    if not w: raise HTTPException(404, "Not found")
    background.add_task(_deliver_webhook, str(w.id), p.event, json.dumps(p.payload))
    return {"queued": True}

async def _deliver_webhook(hook_id: str, event: str, payload_json: str):
    """Queue + deliver a webhook with HMAC signing and retry scheduling.
    Thin shim over `app.services.webhooks.queue_delivery` so existing callers
    keep working without changes."""
    from app.services.webhooks import queue_delivery
    await queue_delivery(hook_id, event, payload_json)

@router.get("/webhooks/{hook_id}/deliveries")
async def list_deliveries(hook_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WebhookDelivery).where(WebhookDelivery.webhook_id == hook_id).order_by(WebhookDelivery.created_at.desc()).limit(50))
    return [{
        "id": str(d.id), "event": d.event, "status_code": d.status_code, "error": d.error,
        "attempts": d.attempts, "next_attempt_at": d.next_attempt_at.isoformat() if d.next_attempt_at else None,
        "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    } for d in result.scalars().all()]


@router.post("/webhooks/deliveries/{delivery_id}/retry", dependencies=[Depends(require_permission("admin.webhook.manage"))])
async def retry_delivery(delivery_id: UUID, db: AsyncSession = Depends(get_db)):
    """Force-requeue a delivery by setting next_attempt_at=now. The sweeper
    picks it up on its next tick (or within a minute)."""
    d = await db.get(WebhookDelivery, delivery_id)
    if not d:
        raise HTTPException(404, "Not found")
    d.next_attempt_at = datetime.utcnow()
    await db.commit()
    return {"requeued": True}


# ── API Keys ────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str
    # Space/comma-separated or list form. Canonicalised to comma-separated.
    scopes: str | list[str] = ""

class ApiKeyUpdate(BaseModel):
    scopes: str | list[str] | None = None
    is_active: bool | None = None


def _normalize_scopes(scopes: str | list[str] | None) -> str:
    if not scopes:
        return ""
    if isinstance(scopes, list):
        items = scopes
    else:
        items = [p for p in scopes.replace(",", " ").split() if p]
    # de-dupe while preserving order
    seen: dict[str, None] = {}
    for s in items:
        seen[s.strip()] = None
    return ",".join(k for k in seen.keys() if k)


@router.get("/api-keys")
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return [{
        "id": str(k.id), "name": k.name, "prefix": k.prefix, "is_active": k.is_active,
        "scopes": [s for s in k.scopes.split(",") if s],
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
    } for k in result.scalars().all()]

@router.post("/api-keys", status_code=201, dependencies=[Depends(require_permission("admin.apikey.manage"))])
async def create_api_key(p: ApiKeyCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw = secrets.token_urlsafe(32)
    prefix = raw[:8]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    k = ApiKey(name=p.name, prefix=prefix, key_hash=key_hash, owner_id=current_user.id,
               scopes=_normalize_scopes(p.scopes))
    db.add(k); await db.commit(); await db.refresh(k)
    return {"id": str(k.id), "api_key": f"{prefix}.{raw}", "scopes": [s for s in k.scopes.split(",") if s],
            "warning": "Save this now — it will not be shown again"}

@router.patch("/api-keys/{key_id}", dependencies=[Depends(require_permission("admin.apikey.manage"))])
async def update_api_key(key_id: UUID, p: ApiKeyUpdate, db: AsyncSession = Depends(get_db)):
    k = await db.get(ApiKey, key_id)
    if not k: raise HTTPException(404, "Not found")
    if p.scopes is not None:
        k.scopes = _normalize_scopes(p.scopes)
    if p.is_active is not None:
        k.is_active = p.is_active
    await db.commit()
    return {"id": str(k.id), "scopes": [s for s in k.scopes.split(",") if s], "is_active": k.is_active}

@router.delete("/api-keys/{key_id}", status_code=204, dependencies=[Depends(require_permission("admin.apikey.manage"))])
async def revoke_api_key(key_id: UUID, db: AsyncSession = Depends(get_db)):
    k = await db.get(ApiKey, key_id)
    if not k: raise HTTPException(404, "Not found")
    k.is_active = False
    await db.commit()


# ── Audit Log ───────────────────────────────────────────────────────

class AuditEntryCreate(BaseModel):
    domain: str; action: str; entity_type: str; entity_id: str | None = None
    before_data: str | None = None; after_data: str | None = None

@router.get("/audit")
async def list_audit(domain: str | None = None, entity_type: str | None = None,
                     entity_id: str | None = None, user_id: UUID | None = None,
                     limit: int = 200, db: AsyncSession = Depends(get_db)):
    q = select(AuditEntry).order_by(AuditEntry.created_at.desc()).limit(min(limit, 500))
    if domain: q = q.where(AuditEntry.domain == domain)
    if entity_type: q = q.where(AuditEntry.entity_type == entity_type)
    if entity_id: q = q.where(AuditEntry.entity_id == entity_id)
    if user_id: q = q.where(AuditEntry.user_id == user_id)
    result = await db.execute(q)
    return [{"id": str(a.id), "user_id": str(a.user_id) if a.user_id else None,
             "domain": a.domain, "action": a.action, "entity_type": a.entity_type, "entity_id": a.entity_id,
             "before_data": a.before_data, "after_data": a.after_data,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in result.scalars().all()]

@router.post("/audit", status_code=201)
async def log_audit(p: AuditEntryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = AuditEntry(user_id=current_user.id, domain=p.domain, action=p.action,
                   entity_type=p.entity_type, entity_id=p.entity_id,
                   before_data=p.before_data, after_data=p.after_data)
    db.add(a); await db.commit(); await db.refresh(a)
    return {"id": str(a.id)}


# ── Scheduled Reports ───────────────────────────────────────────────

class ScheduledReportCreate(BaseModel):
    name: str; endpoint: str; frequency: ReportFrequency = ReportFrequency.WEEKLY
    recipients: str = ""

def _next_run(freq: ReportFrequency, now: datetime) -> datetime:
    if freq == ReportFrequency.DAILY: return now + timedelta(days=1)
    if freq == ReportFrequency.WEEKLY: return now + timedelta(days=7)
    return now + timedelta(days=30)

@router.get("/scheduled-reports")
async def list_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledReport).order_by(ScheduledReport.name))
    return [{"id": str(r.id), "name": r.name, "endpoint": r.endpoint, "frequency": r.frequency.value,
             "recipients": r.recipients, "next_run": r.next_run.isoformat() if r.next_run else None,
             "last_run": r.last_run.isoformat() if r.last_run else None, "is_active": r.is_active}
            for r in result.scalars().all()]

@router.post("/scheduled-reports", status_code=201, dependencies=[Depends(require_permission("admin.workspace.manage"))])
async def create_schedule(p: ScheduledReportCreate, db: AsyncSession = Depends(get_db)):
    r = ScheduledReport(name=p.name, endpoint=p.endpoint, frequency=p.frequency, recipients=p.recipients,
                        next_run=_next_run(p.frequency, datetime.utcnow()))
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

@router.post("/scheduled-reports/run", dependencies=[Depends(require_permission("admin.workspace.manage"))])
async def run_due_reports(db: AsyncSession = Depends(get_db)):
    """Run all reports whose next_run <= now. Stores result in runs table, updates next_run."""
    now = datetime.utcnow()
    due = (await db.execute(select(ScheduledReport).where(ScheduledReport.is_active == True, ScheduledReport.next_run <= now))).scalars().all()
    ran = 0
    try:
        import httpx
    except Exception:
        httpx = None  # type: ignore
    for r in due:
        status = "ok"; err = None; result_json = None
        if httpx is None:
            status = "error"; err = "httpx not installed"
        else:
            try:
                # Relative endpoint — just capture; delivery would use recipients
                result_json = json.dumps({"scheduled": r.name, "endpoint": r.endpoint, "run_at": now.isoformat()})
            except Exception as e:
                status = "error"; err = str(e)[:1000]
        db.add(ScheduledReportRun(report_id=r.id, status=status, result_json=result_json, error=err))
        r.last_run = now
        r.next_run = _next_run(r.frequency, now)
        ran += 1
    await db.commit()
    return {"ran": ran}

@router.get("/scheduled-reports/{report_id}/runs")
async def list_report_runs(report_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledReportRun).where(ScheduledReportRun.report_id == report_id).order_by(ScheduledReportRun.ran_at.desc()).limit(50))
    return [{"id": str(r.id), "status": r.status, "error": r.error,
             "ran_at": r.ran_at.isoformat() if r.ran_at else None}
            for r in result.scalars().all()]


# ── Dashboard Builder ───────────────────────────────────────────────

class WidgetIn(BaseModel):
    title: str; widget_type: str = "stat"; endpoint: str
    json_path: str | None = None; position: int = 0; config: str | None = None

class DashboardCreate(BaseModel):
    name: str; is_shared: bool = False; widgets: list[WidgetIn] = []

@router.get("/dashboards")
async def list_dashboards(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Dashboard).where(or_(Dashboard.owner_id == current_user.id, Dashboard.is_shared == True))
    result = await db.execute(q)
    return [{"id": str(d.id), "name": d.name, "is_shared": d.is_shared,
             "owner_id": str(d.owner_id) if d.owner_id else None}
            for d in result.scalars().all()]

@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: UUID, db: AsyncSession = Depends(get_db)):
    d = await db.get(Dashboard, dashboard_id)
    if not d: raise HTTPException(404, "Not found")
    widgets = (await db.execute(select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id).order_by(DashboardWidget.position))).scalars().all()
    return {"id": str(d.id), "name": d.name, "is_shared": d.is_shared,
            "widgets": [{"id": str(w.id), "title": w.title, "widget_type": w.widget_type,
                         "endpoint": w.endpoint, "json_path": w.json_path, "position": w.position, "config": w.config}
                        for w in widgets]}

@router.post("/dashboards", status_code=201)
async def create_dashboard(p: DashboardCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = Dashboard(name=p.name, owner_id=current_user.id, is_shared=p.is_shared)
    db.add(d); await db.flush()
    for w in p.widgets:
        db.add(DashboardWidget(dashboard_id=d.id, title=w.title, widget_type=w.widget_type,
                               endpoint=w.endpoint, json_path=w.json_path, position=w.position, config=w.config))
    await db.commit(); await db.refresh(d)
    return {"id": str(d.id)}

@router.post("/dashboards/{dashboard_id}/widgets", status_code=201)
async def add_widget(dashboard_id: UUID, w: WidgetIn, db: AsyncSession = Depends(get_db)):
    widget = DashboardWidget(dashboard_id=dashboard_id, title=w.title, widget_type=w.widget_type,
                             endpoint=w.endpoint, json_path=w.json_path, position=w.position, config=w.config)
    db.add(widget); await db.commit(); await db.refresh(widget)
    return {"id": str(widget.id)}

@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: UUID, db: AsyncSession = Depends(get_db)):
    d = await db.get(Dashboard, dashboard_id)
    if not d: raise HTTPException(404, "Not found")
    await db.delete(d); await db.commit()


# ── SSO (stub) ──────────────────────────────────────────────────────

class SsoProviderCreate(BaseModel):
    name: str; provider_type: SsoProviderType = SsoProviderType.OIDC
    issuer_url: str | None = None; client_id: str | None = None; client_secret: str | None = None
    metadata_xml_url: str | None = None

@router.get("/sso/providers")
async def list_sso(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SsoProvider).order_by(SsoProvider.name))
    return [{"id": str(p.id), "name": p.name, "provider_type": p.provider_type.value,
             "issuer_url": p.issuer_url, "is_active": p.is_active}
            for p in result.scalars().all()]

@router.post("/sso/providers", status_code=201, dependencies=[Depends(require_permission("admin.sso.manage"))])
async def create_sso(p: SsoProviderCreate, db: AsyncSession = Depends(get_db)):
    masked = f"****{p.client_secret[-4:]}" if p.client_secret and len(p.client_secret) >= 4 else None
    prov = SsoProvider(name=p.name, provider_type=p.provider_type, issuer_url=p.issuer_url,
                       client_id=p.client_id, client_secret_masked=masked, metadata_xml_url=p.metadata_xml_url)
    db.add(prov); await db.commit(); await db.refresh(prov)
    return {"id": str(prov.id)}

# SSO authorize / callback now live in app/routers/sso.py (#48)


# ── Workspaces (stub multi-tenancy) ─────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str; slug: str; plan: str = "free"

class WorkspaceMemberAdd(BaseModel):
    user_id: UUID; role: str = "member"

@router.get("/workspaces")
async def list_workspaces(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    memberships = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == current_user.id))).scalars().all()
    ws_ids = [m.workspace_id for m in memberships]
    # Also include workspaces the user owns
    owned = (await db.execute(select(Workspace).where(Workspace.owner_id == current_user.id))).scalars().all()
    ids = set(ws_ids) | {o.id for o in owned}
    if not ids: return []
    result = await db.execute(select(Workspace).where(Workspace.id.in_(ids)))
    return [{"id": str(w.id), "name": w.name, "slug": w.slug, "plan": w.plan,
             "owner_id": str(w.owner_id) if w.owner_id else None}
            for w in result.scalars().all()]

@router.post("/workspaces", status_code=201, dependencies=[Depends(require_permission("admin.workspace.manage"))])
async def create_workspace(p: WorkspaceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Workspace).where(Workspace.slug == p.slug))).scalar_one_or_none()
    if existing: raise HTTPException(400, "Slug already exists")
    w = Workspace(name=p.name, slug=p.slug, plan=p.plan, owner_id=current_user.id)
    db.add(w); await db.flush()
    db.add(WorkspaceMember(workspace_id=w.id, user_id=current_user.id, role="owner"))
    await db.commit(); await db.refresh(w)
    return {"id": str(w.id), "slug": w.slug}

@router.post("/workspaces/{ws_id}/members", status_code=201, dependencies=[Depends(require_permission("admin.workspace.manage"))])
async def add_workspace_member(ws_id: UUID, p: WorkspaceMemberAdd, db: AsyncSession = Depends(get_db)):
    from app.services.plans import check_can_add_member
    await check_can_add_member(db, ws_id)
    m = WorkspaceMember(workspace_id=ws_id, user_id=p.user_id, role=p.role)
    db.add(m); await db.commit(); await db.refresh(m)
    return {"id": str(m.id)}

@router.get("/workspaces/{ws_id}/members")
async def list_ws_members(ws_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id))
    return [{"id": str(m.id), "user_id": str(m.user_id), "role": m.role,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in result.scalars().all()]
