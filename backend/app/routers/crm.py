"""CRM System: Companies, Contacts, Leads, Opportunities, Interactions, Quotes, Campaigns."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import apply_field_mask, get_field_mask, require_permission
from app.services.workspaces import get_active_workspace_id
from fastapi import Request
from app.database import get_db
from app.dependencies import get_current_user
from app.models.crm import (
    Company, Contact, Lead, LeadStatus, LeadSource,
    Opportunity, OpportunityStage, Interaction, InteractionType,
    Quote, QuoteItem, QuoteStatus, Campaign, CampaignMember, CampaignStatus,
    EmailMessage, EmailDirection, Contract, ContractStatus, BillingCycle,
    CommissionRule, Commission, Territory,
    DripSequence, DripStep, DripEnrollment, HealthSnapshot,
)
from app.models.erp import Invoice, InvoiceItem, InvoiceType, InvoiceStatus
from app.models.user import User

router = APIRouter(prefix="/api/crm", tags=["crm"], dependencies=[Depends(get_current_user)])


# ── Companies ───────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str; industry: str | None = None; website: str | None = None; phone: str | None = None; address: str | None = None; annual_revenue: float | None = None; employee_count: int | None = None; notes: str | None = None

@router.get("/companies")
async def list_companies(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Company).order_by(Company.name).limit(200)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Company.workspace_id == ws_id) | (Company.workspace_id.is_(None)))
    result = await db.execute(q)
    masked = await get_field_mask(db, current_user, "company", request=request)
    return [
        apply_field_mask(
            {"id": str(c.id), "name": c.name, "industry": c.industry, "website": c.website, "phone": c.phone, "annual_revenue": c.annual_revenue, "employee_count": c.employee_count},
            masked,
        )
        for c in result.scalars().all()
    ]

@router.post("/companies", status_code=201, dependencies=[Depends(require_permission("sales.company.manage"))])
async def create_company(
    p: CompanyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_id = await get_active_workspace_id(request, current_user, db)
    c = Company(**p.model_dump(), workspace_id=ws_id)
    db.add(c); await db.commit(); await db.refresh(c)
    return {"id": str(c.id), "name": c.name}

@router.delete("/companies/{company_id}", status_code=204, dependencies=[Depends(require_permission("sales.company.manage"))])
async def delete_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(Company, company_id)
    if not c: raise HTTPException(404, "Company not found")
    await db.delete(c); await db.commit()


# ── Contacts ────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    company_id: UUID | None = None; first_name: str; last_name: str | None = None; email: str | None = None; phone: str | None = None; job_title: str | None = None; notes: str | None = None

@router.get("/contacts")
async def list_contacts(
    request: Request,
    company_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Contact).order_by(Contact.first_name).limit(200)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Contact.workspace_id == ws_id) | (Contact.workspace_id.is_(None)))
    if company_id: q = q.where(Contact.company_id == company_id)
    result = await db.execute(q)
    return [{"id": str(c.id), "first_name": c.first_name, "last_name": c.last_name, "email": c.email, "phone": c.phone, "job_title": c.job_title, "company_id": str(c.company_id) if c.company_id else None} for c in result.scalars().all()]

@router.post("/contacts", status_code=201, dependencies=[Depends(require_permission("sales.contact.manage"))])
async def create_contact(
    p: ContactCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_id = await get_active_workspace_id(request, current_user, db)
    c = Contact(**p.model_dump(), workspace_id=ws_id); db.add(c); await db.commit(); await db.refresh(c)
    return {"id": str(c.id), "first_name": c.first_name}

@router.delete("/contacts/{contact_id}", status_code=204, dependencies=[Depends(require_permission("sales.contact.manage"))])
async def delete_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(Contact, contact_id)
    if not c: raise HTTPException(404, "Contact not found")
    await db.delete(c); await db.commit()


# ── Leads ───────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    contact_name: str; company_name: str | None = None; email: str | None = None; phone: str | None = None; source: LeadSource = LeadSource.OTHER; estimated_value: float | None = None; notes: str | None = None

@router.get("/leads")
async def list_leads(
    request: Request,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Lead).order_by(Lead.created_at.desc()).limit(200)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Lead.workspace_id == ws_id) | (Lead.workspace_id.is_(None)))
    if status: q = q.where(cast(Lead.status, String) == status.upper())
    result = await db.execute(q)
    return [{"id": str(l.id), "contact_name": l.contact_name, "company_name": l.company_name, "email": l.email, "source": l.source.value, "status": l.status.value, "estimated_value": l.estimated_value} for l in result.scalars().all()]

@router.post("/leads", status_code=201, dependencies=[Depends(require_permission("sales.lead.create"))])
async def create_lead(
    p: LeadCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_id = await get_active_workspace_id(request, current_user, db)
    l = Lead(**p.model_dump(), workspace_id=ws_id); db.add(l); await db.commit(); await db.refresh(l)
    return {"id": str(l.id), "contact_name": l.contact_name}

@router.patch("/leads/{lead_id}", dependencies=[Depends(require_permission("sales.lead.update_status"))])
async def update_lead_status(lead_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    l = await db.get(Lead, lead_id)
    if not l: raise HTTPException(404, "Lead not found")
    l.status = LeadStatus(status); await db.commit()
    return {"id": str(l.id), "status": l.status.value}


# ── Opportunities ───────────────────────────────────────────────────

class OpportunityCreate(BaseModel):
    company_id: UUID | None = None; contact_id: UUID | None = None; title: str; description: str | None = None; stage: OpportunityStage = OpportunityStage.PROSPECTING; amount: float | None = None; probability: int | None = None; expected_close: str | None = None

@router.get("/opportunities")
async def list_opportunities(
    request: Request,
    stage: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Opportunity).order_by(Opportunity.created_at.desc()).limit(200)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Opportunity.workspace_id == ws_id) | (Opportunity.workspace_id.is_(None)))
    if stage: q = q.where(cast(Opportunity.stage, String) == stage.upper())
    result = await db.execute(q)
    return [{"id": str(o.id), "title": o.title, "stage": o.stage.value, "amount": o.amount, "probability": o.probability, "expected_close": o.expected_close.isoformat()[:10] if o.expected_close else None, "company_id": str(o.company_id) if o.company_id else None} for o in result.scalars().all()]

@router.post("/opportunities", status_code=201, dependencies=[Depends(require_permission("sales.opportunity.manage"))])
async def create_opportunity(
    p: OpportunityCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    ws_id = await get_active_workspace_id(request, current_user, db)
    o = Opportunity(**{**p.model_dump(exclude={"expected_close"}), "expected_close": datetime.fromisoformat(p.expected_close) if p.expected_close else None}, workspace_id=ws_id)
    db.add(o); await db.commit(); await db.refresh(o)
    return {"id": str(o.id), "title": o.title}

@router.patch("/opportunities/{opp_id}", dependencies=[Depends(require_permission("sales.opportunity.manage"))])
async def update_opportunity_stage(opp_id: UUID, stage: str = Query(...), db: AsyncSession = Depends(get_db)):
    o = await db.get(Opportunity, opp_id)
    if not o: raise HTTPException(404, "Opportunity not found")
    o.stage = OpportunityStage(stage); await db.commit()
    return {"id": str(o.id), "stage": o.stage.value}


# ── Interactions ────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    contact_id: UUID | None = None; opportunity_id: UUID | None = None; interaction_type: InteractionType = InteractionType.NOTE; subject: str; body: str | None = None

@router.get("/interactions")
async def list_interactions(contact_id: UUID | None = None, opportunity_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Interaction).order_by(Interaction.interaction_date.desc()).limit(100)
    if contact_id: q = q.where(Interaction.contact_id == contact_id)
    if opportunity_id: q = q.where(Interaction.opportunity_id == opportunity_id)
    result = await db.execute(q)
    return [{"id": str(i.id), "interaction_type": i.interaction_type.value, "subject": i.subject, "body": i.body, "interaction_date": i.interaction_date.isoformat()[:10] if i.interaction_date else None} for i in result.scalars().all()]

@router.post("/interactions", status_code=201)
async def create_interaction(p: InteractionCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    i = Interaction(**p.model_dump(), user_id=current_user.id); db.add(i); await db.commit(); await db.refresh(i)
    return {"id": str(i.id), "subject": i.subject}


# ── CRM Dashboard ──────────────────────────────────────────────────

@router.get("/dashboard")
async def crm_dashboard(db: AsyncSession = Depends(get_db)):
    companies = await db.scalar(select(func.count(Company.id))) or 0
    contacts = await db.scalar(select(func.count(Contact.id))) or 0
    leads = await db.scalar(select(func.count(Lead.id)).where(Lead.status.notin_([LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED]))) or 0
    open_opps = await db.scalar(select(func.count(Opportunity.id)).where(Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]))) or 0
    pipeline_value = await db.scalar(select(func.coalesce(func.sum(Opportunity.amount), 0)).where(Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]))) or 0
    won_value = await db.scalar(select(func.coalesce(func.sum(Opportunity.amount), 0)).where(Opportunity.stage == OpportunityStage.CLOSED_WON)) or 0

    # Pipeline by stage
    stage_result = await db.execute(
        select(cast(Opportunity.stage, String), func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0))
        .group_by(Opportunity.stage)
    )
    pipeline = [{"stage": r[0].lower(), "count": r[1], "value": round(r[2], 2)} for r in stage_result.all()]

    return {
        "companies": companies, "contacts": contacts, "active_leads": leads,
        "open_opportunities": open_opps, "pipeline_value": round(pipeline_value, 2),
        "won_value": round(won_value, 2), "pipeline_by_stage": pipeline,
    }


# ── Sales Forecast ──────────────────────────────────────────────────

DEFAULT_STAGE_PROB = {
    OpportunityStage.PROSPECTING: 10, OpportunityStage.QUALIFICATION: 25,
    OpportunityStage.PROPOSAL: 50, OpportunityStage.NEGOTIATION: 75,
    OpportunityStage.CLOSED_WON: 100, OpportunityStage.CLOSED_LOST: 0,
}

@router.get("/forecast")
async def sales_forecast(db: AsyncSession = Depends(get_db)):
    opps = (await db.execute(select(Opportunity).where(Opportunity.stage.notin_([OpportunityStage.CLOSED_LOST])))).scalars().all()
    weighted = 0.0
    by_stage: dict[str, dict] = {}
    by_month: dict[str, dict] = {}
    for o in opps:
        amt = o.amount or 0
        prob = (o.probability if o.probability is not None else DEFAULT_STAGE_PROB.get(o.stage, 0)) / 100
        w = amt * prob
        weighted += w
        s = by_stage.setdefault(o.stage.value, {"stage": o.stage.value, "count": 0, "amount": 0.0, "weighted": 0.0})
        s["count"] += 1; s["amount"] += amt; s["weighted"] += w
        if o.expected_close:
            k = o.expected_close.strftime("%Y-%m")
            m = by_month.setdefault(k, {"month": k, "amount": 0.0, "weighted": 0.0, "count": 0})
            m["amount"] += amt; m["weighted"] += w; m["count"] += 1
    return {
        "weighted_total": round(weighted, 2),
        "by_stage": [{**v, "amount": round(v["amount"], 2), "weighted": round(v["weighted"], 2)} for v in by_stage.values()],
        "by_month": sorted([{**v, "amount": round(v["amount"], 2), "weighted": round(v["weighted"], 2)} for v in by_month.values()], key=lambda x: x["month"]),
    }


# ── Lead Scoring ────────────────────────────────────────────────────

def _compute_score(l: Lead) -> int:
    score = 0
    if l.email: score += 10
    if l.phone: score += 10
    if l.company_name: score += 15
    if l.estimated_value and l.estimated_value > 10000: score += 30
    elif l.estimated_value and l.estimated_value > 1000: score += 15
    if l.source in (LeadSource.REFERRAL, LeadSource.EVENT): score += 25
    if l.source == LeadSource.WEBSITE: score += 10
    if l.status == LeadStatus.QUALIFIED: score += 20
    return min(100, score)

@router.post("/leads/{lead_id}/score")
async def score_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    l = await db.get(Lead, lead_id)
    if not l: raise HTTPException(404, "Lead not found")
    l.score = _compute_score(l)
    await db.commit()
    return {"id": str(l.id), "score": l.score}

@router.post("/leads/score-all")
async def score_all_leads(db: AsyncSession = Depends(get_db)):
    leads = (await db.execute(select(Lead).where(Lead.status.notin_([LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED])))).scalars().all()
    for l in leads: l.score = _compute_score(l)
    await db.commit()
    return {"scored": len(leads)}


# ── Follow-ups ──────────────────────────────────────────────────────

class InteractionFollowUp(BaseModel):
    follow_up_date: str | None = None

@router.patch("/interactions/{interaction_id}/follow-up")
async def set_follow_up(interaction_id: UUID, p: InteractionFollowUp, db: AsyncSession = Depends(get_db)):
    i = await db.get(Interaction, interaction_id)
    if not i: raise HTTPException(404, "Interaction not found")
    i.follow_up_date = datetime.fromisoformat(p.follow_up_date) if p.follow_up_date else None
    i.follow_up_done = False
    await db.commit()
    return {"id": str(i.id), "follow_up_date": i.follow_up_date.isoformat()[:10] if i.follow_up_date else None}

@router.post("/interactions/{interaction_id}/follow-up/done")
async def complete_follow_up(interaction_id: UUID, db: AsyncSession = Depends(get_db)):
    i = await db.get(Interaction, interaction_id)
    if not i: raise HTTPException(404, "Interaction not found")
    i.follow_up_done = True
    await db.commit()
    return {"id": str(i.id), "follow_up_done": True}

@router.get("/follow-ups/due")
async def follow_ups_due(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(select(Interaction).where(Interaction.follow_up_date.isnot(None), Interaction.follow_up_done == False, Interaction.follow_up_date <= now).order_by(Interaction.follow_up_date))
    return [{"id": str(i.id), "subject": i.subject, "contact_id": str(i.contact_id) if i.contact_id else None, "follow_up_date": i.follow_up_date.isoformat()[:10] if i.follow_up_date else None} for i in result.scalars().all()]


# ── Quotes ──────────────────────────────────────────────────────────

class QuoteItemIn(BaseModel):
    description: str; quantity: float = 1.0; unit_price: float = 0.0

class QuoteCreate(BaseModel):
    opportunity_id: UUID | None = None; company_id: UUID | None = None; contact_id: UUID | None = None
    quote_number: str; tax_rate: float = 0.0; valid_until: str | None = None; notes: str | None = None
    items: list[QuoteItemIn] = []

@router.get("/quotes")
async def list_quotes(
    request: Request,
    opportunity_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Quote).order_by(Quote.created_at.desc()).limit(200)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Quote.workspace_id == ws_id) | (Quote.workspace_id.is_(None)))
    if opportunity_id: q = q.where(Quote.opportunity_id == opportunity_id)
    result = await db.execute(q)
    return [{"id": str(qt.id), "quote_number": qt.quote_number, "status": qt.status.value, "total": qt.total, "valid_until": qt.valid_until.isoformat()[:10] if qt.valid_until else None, "company_id": str(qt.company_id) if qt.company_id else None, "opportunity_id": str(qt.opportunity_id) if qt.opportunity_id else None, "invoice_id": str(qt.invoice_id) if qt.invoice_id else None} for qt in result.scalars().all()]

@router.post("/quotes", status_code=201, dependencies=[Depends(require_permission("sales.quote.manage"))])
async def create_quote(
    p: QuoteCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_id = await get_active_workspace_id(request, current_user, db)
    subtotal = sum((i.quantity or 1) * (i.unit_price or 0) for i in p.items)
    tax = subtotal * p.tax_rate / 100
    q = Quote(opportunity_id=p.opportunity_id, company_id=p.company_id, contact_id=p.contact_id,
              quote_number=p.quote_number, subtotal=round(subtotal, 2), tax_rate=p.tax_rate,
              total=round(subtotal + tax, 2), notes=p.notes,
              valid_until=datetime.fromisoformat(p.valid_until) if p.valid_until else None,
              workspace_id=ws_id)
    db.add(q); await db.flush()
    for i in p.items:
        amt = (i.quantity or 1) * (i.unit_price or 0)
        db.add(QuoteItem(quote_id=q.id, description=i.description, quantity=i.quantity, unit_price=i.unit_price, amount=round(amt, 2)))
    await db.commit(); await db.refresh(q)
    return {"id": str(q.id), "quote_number": q.quote_number, "total": q.total}

@router.patch("/quotes/{quote_id}", dependencies=[Depends(require_permission("sales.quote.manage"))])
async def update_quote_status(quote_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    q = await db.get(Quote, quote_id)
    if not q: raise HTTPException(404, "Quote not found")
    q.status = QuoteStatus(status); await db.commit()
    return {"id": str(q.id), "status": q.status.value}

@router.post("/quotes/{quote_id}/convert", dependencies=[Depends(require_permission("sales.quote.manage"))])
async def convert_quote_to_invoice(quote_id: UUID, db: AsyncSession = Depends(get_db)):
    q = await db.get(Quote, quote_id)
    if not q: raise HTTPException(404, "Quote not found")
    if q.invoice_id: raise HTTPException(400, "Quote already converted")
    items = (await db.execute(select(QuoteItem).where(QuoteItem.quote_id == quote_id))).scalars().all()
    tax_amount = q.subtotal * q.tax_rate / 100
    inv = Invoice(invoice_number=f"INV-FROM-{q.quote_number}", invoice_type=InvoiceType.RECEIVABLE,
                  subtotal=q.subtotal, tax_rate=q.tax_rate, tax_amount=round(tax_amount, 2),
                  total=round(q.subtotal + tax_amount, 2), notes=f"Converted from quote {q.quote_number}")
    db.add(inv); await db.flush()
    for it in items:
        db.add(InvoiceItem(invoice_id=inv.id, description=it.description, quantity=it.quantity, unit_price=it.unit_price, amount=it.amount))
    q.invoice_id = inv.id
    q.status = QuoteStatus.CONVERTED
    await db.commit()
    return {"quote_id": str(q.id), "invoice_id": str(inv.id), "invoice_number": inv.invoice_number}


# ── Campaigns ───────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str; status: CampaignStatus = CampaignStatus.PLANNED
    start_date: str | None = None; end_date: str | None = None
    budget: float = 0.0; actual_cost: float = 0.0; description: str | None = None

class CampaignMemberAdd(BaseModel):
    contact_id: UUID | None = None; lead_id: UUID | None = None; status: str = "targeted"

@router.get("/campaigns")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()).limit(100))
    return [{"id": str(c.id), "name": c.name, "status": c.status.value, "budget": c.budget, "actual_cost": c.actual_cost, "start_date": c.start_date.isoformat()[:10] if c.start_date else None, "end_date": c.end_date.isoformat()[:10] if c.end_date else None} for c in result.scalars().all()]

@router.post("/campaigns", status_code=201, dependencies=[Depends(require_permission("sales.campaign.manage"))])
async def create_campaign(p: CampaignCreate, db: AsyncSession = Depends(get_db)):
    c = Campaign(name=p.name, status=p.status, budget=p.budget, actual_cost=p.actual_cost, description=p.description,
                 start_date=datetime.fromisoformat(p.start_date) if p.start_date else None,
                 end_date=datetime.fromisoformat(p.end_date) if p.end_date else None)
    db.add(c); await db.commit(); await db.refresh(c)
    return {"id": str(c.id), "name": c.name}

@router.post("/campaigns/{campaign_id}/members", status_code=201)
async def add_campaign_member(campaign_id: UUID, p: CampaignMemberAdd, db: AsyncSession = Depends(get_db)):
    m = CampaignMember(campaign_id=campaign_id, contact_id=p.contact_id, lead_id=p.lead_id, status=p.status)
    db.add(m); await db.commit(); await db.refresh(m)
    return {"id": str(m.id)}

@router.get("/campaigns/{campaign_id}/roi")
async def campaign_roi(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(Campaign, campaign_id)
    if not c: raise HTTPException(404, "Campaign not found")
    members = (await db.execute(select(CampaignMember).where(CampaignMember.campaign_id == campaign_id))).scalars().all()
    lead_ids = [m.lead_id for m in members if m.lead_id]
    converted = 0
    revenue = 0.0
    if lead_ids:
        conv_leads = (await db.execute(select(Lead).where(Lead.id.in_(lead_ids), Lead.status == LeadStatus.CONVERTED))).scalars().all()
        converted = len(conv_leads)
        revenue = sum(l.estimated_value or 0 for l in conv_leads)
    roi = ((revenue - c.actual_cost) / c.actual_cost * 100) if c.actual_cost else 0
    return {"campaign_id": str(c.id), "members": len(members), "responded": sum(1 for m in members if m.responded),
            "converted": converted, "revenue": round(revenue, 2), "cost": c.actual_cost, "roi_pct": round(roi, 1)}


# ── Email Sync ──────────────────────────────────────────────────────

class EmailIngest(BaseModel):
    external_id: str | None = None; thread_id: str | None = None
    direction: EmailDirection = EmailDirection.INBOUND
    from_email: str; to_email: str; subject: str | None = None; body: str | None = None
    sent_at: str | None = None

@router.get("/emails")
async def list_emails(contact_id: UUID | None = None, thread_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(EmailMessage).order_by(EmailMessage.sent_at.desc()).limit(200)
    if contact_id: q = q.where(EmailMessage.contact_id == contact_id)
    if thread_id: q = q.where(EmailMessage.thread_id == thread_id)
    result = await db.execute(q)
    return [{"id": str(e.id), "direction": e.direction.value, "from_email": e.from_email, "to_email": e.to_email,
             "subject": e.subject, "body": e.body, "sent_at": e.sent_at.isoformat() if e.sent_at else None,
             "contact_id": str(e.contact_id) if e.contact_id else None, "thread_id": e.thread_id}
            for e in result.scalars().all()]

@router.post("/emails/ingest", status_code=201)
async def ingest_email(p: EmailIngest, db: AsyncSession = Depends(get_db)):
    # Auto-link to contact by email
    contact_id = None
    target = p.from_email if p.direction == EmailDirection.INBOUND else p.to_email
    c = (await db.execute(select(Contact).where(Contact.email == target).limit(1))).scalar_one_or_none()
    if c: contact_id = c.id
    e = EmailMessage(external_id=p.external_id, thread_id=p.thread_id, direction=p.direction,
                     from_email=p.from_email, to_email=p.to_email, subject=p.subject, body=p.body,
                     sent_at=datetime.fromisoformat(p.sent_at) if p.sent_at else datetime.now(timezone.utc),
                     contact_id=contact_id)
    db.add(e); await db.commit(); await db.refresh(e)
    return {"id": str(e.id), "linked_contact": str(contact_id) if contact_id else None}


# ── Contracts ───────────────────────────────────────────────────────

class ContractCreate(BaseModel):
    company_id: UUID; opportunity_id: UUID | None = None
    contract_number: str; status: ContractStatus = ContractStatus.DRAFT
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    amount: float; start_date: str; end_date: str | None = None
    auto_renew: bool = False; notes: str | None = None

def _mrr_of(c: Contract) -> float:
    if c.billing_cycle == BillingCycle.MONTHLY: return c.amount
    if c.billing_cycle == BillingCycle.QUARTERLY: return c.amount / 3
    if c.billing_cycle == BillingCycle.YEARLY: return c.amount / 12
    return 0  # one-time

@router.get("/contracts")
async def list_contracts(company_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Contract).order_by(Contract.created_at.desc()).limit(200)
    if company_id: q = q.where(Contract.company_id == company_id)
    result = await db.execute(q)
    return [{"id": str(c.id), "contract_number": c.contract_number, "status": c.status.value,
             "billing_cycle": c.billing_cycle.value, "amount": c.amount, "mrr": round(_mrr_of(c), 2),
             "start_date": c.start_date.isoformat()[:10] if c.start_date else None,
             "end_date": c.end_date.isoformat()[:10] if c.end_date else None,
             "auto_renew": c.auto_renew, "company_id": str(c.company_id)}
            for c in result.scalars().all()]

@router.post("/contracts", status_code=201, dependencies=[Depends(require_permission("sales.contract.manage"))])
async def create_contract(p: ContractCreate, db: AsyncSession = Depends(get_db)):
    c = Contract(company_id=p.company_id, opportunity_id=p.opportunity_id, contract_number=p.contract_number,
                 status=p.status, billing_cycle=p.billing_cycle, amount=p.amount,
                 start_date=datetime.fromisoformat(p.start_date),
                 end_date=datetime.fromisoformat(p.end_date) if p.end_date else None,
                 auto_renew=p.auto_renew, notes=p.notes)
    db.add(c); await db.commit(); await db.refresh(c)
    return {"id": str(c.id), "contract_number": c.contract_number}

@router.get("/contracts/metrics")
async def contract_metrics(db: AsyncSession = Depends(get_db)):
    active = (await db.execute(select(Contract).where(Contract.status == ContractStatus.ACTIVE))).scalars().all()
    mrr = sum(_mrr_of(c) for c in active)
    arr = mrr * 12
    renewals_30 = (await db.execute(select(Contract).where(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date.isnot(None),
        Contract.end_date <= datetime.now(timezone.utc) + timedelta(days=30),
    ))).scalars().all()
    churned = (await db.execute(select(func.count(Contract.id)).where(Contract.status == ContractStatus.CHURNED))).scalar() or 0
    return {"active_count": len(active), "mrr": round(mrr, 2), "arr": round(arr, 2),
            "renewals_due_30d": [{"id": str(c.id), "contract_number": c.contract_number,
                                   "end_date": c.end_date.isoformat()[:10] if c.end_date else None,
                                   "amount": c.amount, "auto_renew": c.auto_renew} for c in renewals_30],
            "churned_total": churned}

@router.patch("/contracts/{contract_id}", dependencies=[Depends(require_permission("sales.contract.manage"))])
async def update_contract_status(contract_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    c = await db.get(Contract, contract_id)
    if not c: raise HTTPException(404, "Not found")
    c.status = ContractStatus(status); await db.commit()
    return {"id": str(c.id), "status": c.status.value}


# ── Commissions ─────────────────────────────────────────────────────

class CommissionRuleCreate(BaseModel):
    name: str; user_id: UUID | None = None; percentage: float
    min_amount: float = 0.0; max_amount: float | None = None

@router.get("/commission-rules")
async def list_commission_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommissionRule).order_by(CommissionRule.name))
    return [{"id": str(r.id), "name": r.name, "user_id": str(r.user_id) if r.user_id else None,
             "percentage": r.percentage, "min_amount": r.min_amount, "max_amount": r.max_amount, "is_active": r.is_active}
            for r in result.scalars().all()]

@router.post("/commission-rules", status_code=201, dependencies=[Depends(require_permission("sales.commission.manage"))])
async def create_commission_rule(p: CommissionRuleCreate, db: AsyncSession = Depends(get_db)):
    r = CommissionRule(**p.model_dump())
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

@router.post("/commissions/compute", dependencies=[Depends(require_permission("sales.commission.manage"))])
async def compute_commissions(db: AsyncSession = Depends(get_db)):
    """For each closed-won opportunity without a commission, apply the best matching rule."""
    rules = (await db.execute(select(CommissionRule).where(CommissionRule.is_active == True))).scalars().all()
    opps = (await db.execute(select(Opportunity).where(Opportunity.stage == OpportunityStage.CLOSED_WON))).scalars().all()
    existing = (await db.execute(select(Commission.opportunity_id))).scalars().all()
    existing_ids = set(existing)
    created = 0
    for o in opps:
        if o.id in existing_ids: continue
        if not o.assigned_to_id or not o.amount: continue
        matching = [r for r in rules if (r.user_id is None or r.user_id == o.assigned_to_id)
                    and o.amount >= r.min_amount
                    and (r.max_amount is None or o.amount <= r.max_amount)]
        if not matching: continue
        rule = max(matching, key=lambda r: r.percentage)
        comm = round(o.amount * rule.percentage / 100, 2)
        db.add(Commission(user_id=o.assigned_to_id, opportunity_id=o.id, rule_id=rule.id,
                          base_amount=o.amount, commission=comm))
        created += 1
    await db.commit()
    return {"created": created}

@router.get("/commissions")
async def list_commissions(user_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Commission).order_by(Commission.created_at.desc()).limit(500)
    if user_id: q = q.where(Commission.user_id == user_id)
    result = await db.execute(q)
    return [{"id": str(c.id), "user_id": str(c.user_id), "opportunity_id": str(c.opportunity_id),
             "base_amount": c.base_amount, "commission": c.commission, "paid": c.paid,
             "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in result.scalars().all()]

@router.post("/commissions/{commission_id}/pay", dependencies=[Depends(require_permission("sales.commission.manage"))])
async def pay_commission(commission_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(Commission, commission_id)
    if not c: raise HTTPException(404, "Not found")
    c.paid = True; await db.commit()
    return {"id": str(c.id), "paid": True}


# ── Territories ─────────────────────────────────────────────────────

class TerritoryCreate(BaseModel):
    name: str; rule_region: str | None = None; rule_industry: str | None = None
    rule_min_revenue: float | None = None; owner_id: UUID | None = None

@router.get("/territories")
async def list_territories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Territory).order_by(Territory.name))
    return [{"id": str(t.id), "name": t.name, "rule_region": t.rule_region, "rule_industry": t.rule_industry,
             "rule_min_revenue": t.rule_min_revenue, "owner_id": str(t.owner_id) if t.owner_id else None}
            for t in result.scalars().all()]

@router.post("/territories", status_code=201, dependencies=[Depends(require_permission("sales.territory.manage"))])
async def create_territory(p: TerritoryCreate, db: AsyncSession = Depends(get_db)):
    t = Territory(**p.model_dump())
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id": str(t.id)}

@router.post("/territories/auto-assign")
async def auto_assign_leads(db: AsyncSession = Depends(get_db)):
    """Assign unassigned leads to a territory owner based on company industry/revenue/region (best match)."""
    territories = (await db.execute(select(Territory))).scalars().all()
    leads = (await db.execute(select(Lead).where(Lead.assigned_to_id.is_(None)))).scalars().all()
    assigned = 0
    for l in leads:
        # Try to find company revenue/industry via lead contact
        company = None
        if l.contact_id:
            c = await db.get(Contact, l.contact_id)
            if c and c.company_id:
                company = await db.get(Company, c.company_id)
        best = None; best_score = 0
        for t in territories:
            score = 0
            if t.rule_industry and company and company.industry == t.rule_industry: score += 2
            if t.rule_min_revenue and company and (company.annual_revenue or 0) >= t.rule_min_revenue: score += 1
            if score > best_score: best_score = score; best = t
        if best and best.owner_id:
            l.assigned_to_id = best.owner_id; assigned += 1
    await db.commit()
    return {"assigned": assigned}


# ── Drip Campaigns ──────────────────────────────────────────────────

class DripStepIn(BaseModel):
    step_order: int; delay_days: int = 0; subject: str; body: str

class DripSequenceCreate(BaseModel):
    name: str; steps: list[DripStepIn] = []

@router.get("/drips")
async def list_drips(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DripSequence).order_by(DripSequence.name))
    out = []
    for s in result.scalars().all():
        steps = (await db.execute(select(DripStep).where(DripStep.sequence_id == s.id).order_by(DripStep.step_order))).scalars().all()
        out.append({"id": str(s.id), "name": s.name, "is_active": s.is_active, "step_count": len(steps)})
    return out

@router.post("/drips", status_code=201)
async def create_drip(p: DripSequenceCreate, db: AsyncSession = Depends(get_db)):
    s = DripSequence(name=p.name)
    db.add(s); await db.flush()
    for st in p.steps:
        db.add(DripStep(sequence_id=s.id, step_order=st.step_order, delay_days=st.delay_days, subject=st.subject, body=st.body))
    await db.commit(); await db.refresh(s)
    return {"id": str(s.id)}

class DripEnrollIn(BaseModel):
    sequence_id: UUID; contact_id: UUID

@router.post("/drips/enroll", status_code=201)
async def enroll_drip(p: DripEnrollIn, db: AsyncSession = Depends(get_db)):
    steps = (await db.execute(select(DripStep).where(DripStep.sequence_id == p.sequence_id).order_by(DripStep.step_order))).scalars().all()
    if not steps: raise HTTPException(400, "Sequence has no steps")
    en = DripEnrollment(sequence_id=p.sequence_id, contact_id=p.contact_id, current_step=0,
                        next_step_at=datetime.now(timezone.utc) + timedelta(days=steps[0].delay_days))
    db.add(en); await db.commit(); await db.refresh(en)
    return {"id": str(en.id)}

@router.post("/drips/tick")
async def drip_tick(db: AsyncSession = Depends(get_db)):
    """Advance all enrollments whose next_step_at has passed. Logs EmailMessage + Interaction."""
    now = datetime.now(timezone.utc)
    due = (await db.execute(select(DripEnrollment).where(DripEnrollment.is_active == True, DripEnrollment.next_step_at <= now))).scalars().all()
    sent = 0
    for en in due:
        steps = (await db.execute(select(DripStep).where(DripStep.sequence_id == en.sequence_id).order_by(DripStep.step_order))).scalars().all()
        if en.current_step >= len(steps):
            en.is_active = False; continue
        step = steps[en.current_step]
        contact = await db.get(Contact, en.contact_id)
        if contact and contact.email:
            db.add(EmailMessage(direction=EmailDirection.OUTBOUND, from_email="drip@system",
                                to_email=contact.email, subject=step.subject, body=step.body, contact_id=contact.id))
            sent += 1
        en.current_step += 1
        if en.current_step < len(steps):
            en.next_step_at = now + timedelta(days=steps[en.current_step].delay_days)
        else:
            en.is_active = False
    await db.commit()
    return {"advanced": len(due), "emails_sent": sent}


# ── Health Score ────────────────────────────────────────────────────

@router.post("/health/compute")
async def compute_health(db: AsyncSession = Depends(get_db)):
    """Compute health snapshot for every company."""
    companies = (await db.execute(select(Company))).scalars().all()
    now = datetime.now(timezone.utc)
    created = 0
    for co in companies:
        score = 50; factors = []
        # Recent interaction?
        contacts = (await db.execute(select(Contact.id).where(Contact.company_id == co.id))).scalars().all()
        if contacts:
            recent = await db.scalar(select(func.max(Interaction.interaction_date)).where(Interaction.contact_id.in_(contacts)))
            if recent:
                days = (now - recent.replace(tzinfo=None)).days
                if days < 30: score += 20; factors.append("recent interaction +20")
                elif days > 180: score -= 20; factors.append("no interaction 180d -20")
        # Contracts
        active_contracts = await db.scalar(select(func.count(Contract.id)).where(Contract.company_id == co.id, Contract.status == ContractStatus.ACTIVE))
        if active_contracts:
            score += 15; factors.append(f"active contracts +15")
        churned = await db.scalar(select(func.count(Contract.id)).where(Contract.company_id == co.id, Contract.status == ContractStatus.CHURNED))
        if churned: score -= 30; factors.append("churned contract -30")
        # Open opportunities
        opps = await db.scalar(select(func.count(Opportunity.id)).where(Opportunity.company_id == co.id, Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])))
        if opps: score += 10; factors.append("open opps +10")
        score = max(0, min(100, score))
        db.add(HealthSnapshot(company_id=co.id, score=score, factors="; ".join(factors)))
        created += 1
    await db.commit()
    return {"snapshots": created}

@router.get("/health")
async def list_health(db: AsyncSession = Depends(get_db)):
    """Latest snapshot per company."""
    companies = (await db.execute(select(Company))).scalars().all()
    out = []
    for co in companies:
        snap = (await db.execute(select(HealthSnapshot).where(HealthSnapshot.company_id == co.id).order_by(HealthSnapshot.snapshot_date.desc()).limit(1))).scalar_one_or_none()
        if snap:
            out.append({"company_id": str(co.id), "name": co.name, "score": snap.score, "factors": snap.factors,
                        "date": snap.snapshot_date.isoformat()[:10] if snap.snapshot_date else None})
    return sorted(out, key=lambda x: x["score"])
