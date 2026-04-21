"""ERP System: Accounts, Invoices, Expenses, Vendors, Purchase Orders, Assets, Budgets, Payments, Journal, FX, Bank Recon."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Float, String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.erp import (
    Account, AccountType, Invoice, InvoiceItem, InvoiceStatus, InvoiceType,
    Expense, ExpenseCategory, Vendor, PurchaseOrder, POStatus, Asset, AssetStatus,
    Budget, BudgetLine, Currency, FxRate, Payment, RecurringInvoice, RecurringFrequency,
    JournalEntry, JournalLine, BankTransaction,
    Warehouse, Product, StockMovement, MovementType,
    DepreciationSchedule, DepreciationMethod, CreditNote,
    Requisition, RequisitionItem, RequisitionStatus,
)

router = APIRouter(prefix="/api/erp", tags=["erp"], dependencies=[Depends(get_current_user)])


# ── Accounts ────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    code: str; name: str; account_type: AccountType; description: str | None = None

@router.get("/accounts")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).order_by(Account.code))
    return [{"id": str(a.id), "code": a.code, "name": a.name, "account_type": a.account_type.value, "balance": a.balance, "is_active": a.is_active} for a in result.scalars().all()]

@router.post("/accounts", status_code=201, dependencies=[Depends(require_permission("finance.account.manage"))])
async def create_account(p: AccountCreate, db: AsyncSession = Depends(get_db)):
    a = Account(code=p.code, name=p.name, account_type=p.account_type, description=p.description)
    db.add(a); await db.commit(); await db.refresh(a)
    return {"id": str(a.id), "code": a.code}

# ── Vendors ─────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str; contact_person: str | None = None; email: str | None = None; phone: str | None = None; address: str | None = None; tax_id: str | None = None; payment_terms: str | None = None

@router.get("/vendors")
async def list_vendors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).order_by(Vendor.name))
    return [{"id": str(v.id), "name": v.name, "contact_person": v.contact_person, "email": v.email, "phone": v.phone, "is_active": v.is_active} for v in result.scalars().all()]

@router.post("/vendors", status_code=201, dependencies=[Depends(require_permission("finance.vendor.manage"))])
async def create_vendor(p: VendorCreate, db: AsyncSession = Depends(get_db)):
    v = Vendor(**p.model_dump()); db.add(v); await db.commit(); await db.refresh(v)
    return {"id": str(v.id), "name": v.name}

@router.delete("/vendors/{vendor_id}", status_code=204, dependencies=[Depends(require_permission("finance.vendor.manage"))])
async def delete_vendor(vendor_id: UUID, db: AsyncSession = Depends(get_db)):
    v = await db.get(Vendor, vendor_id)
    if not v: raise HTTPException(404, "Vendor not found")
    await db.delete(v); await db.commit()

# ── Invoices ────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    project_id: UUID | None = None; vendor_id: UUID | None = None; invoice_number: str
    invoice_type: InvoiceType = InvoiceType.RECEIVABLE; due_date: str | None = None
    subtotal: float = 0; tax_rate: float = 0; notes: str | None = None
    items: list[dict] = []

@router.get("/invoices")
async def list_invoices(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Invoice).order_by(Invoice.created_at.desc())
    if project_id: q = q.where(Invoice.project_id == project_id)
    result = await db.execute(q.limit(100))
    return [{"id": str(i.id), "invoice_number": i.invoice_number, "invoice_type": i.invoice_type.value, "status": i.status.value, "total": i.total, "issue_date": i.issue_date.isoformat()[:10] if i.issue_date else None, "due_date": i.due_date.isoformat()[:10] if i.due_date else None} for i in result.scalars().all()]

@router.post("/invoices", status_code=201, dependencies=[Depends(require_permission("finance.invoice.create"))])
async def create_invoice(p: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    tax_amount = p.subtotal * p.tax_rate / 100
    inv = Invoice(project_id=p.project_id, vendor_id=p.vendor_id, invoice_number=p.invoice_number, invoice_type=p.invoice_type, subtotal=p.subtotal, tax_rate=p.tax_rate, tax_amount=round(tax_amount, 2), total=round(p.subtotal + tax_amount, 2), notes=p.notes, due_date=datetime.fromisoformat(p.due_date) if p.due_date else None)
    db.add(inv); await db.flush()
    for item in p.items:
        amt = (item.get("quantity", 1) or 1) * (item.get("unit_price", 0) or 0)
        db.add(InvoiceItem(invoice_id=inv.id, description=item.get("description", ""), quantity=item.get("quantity", 1), unit_price=item.get("unit_price", 0), amount=round(amt, 2)))
    await db.commit(); await db.refresh(inv)
    return {"id": str(inv.id), "invoice_number": inv.invoice_number, "total": inv.total}

@router.patch("/invoices/{invoice_id}", dependencies=[Depends(require_permission("finance.invoice.update_status"))])
async def update_invoice_status(invoice_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    inv = await db.get(Invoice, invoice_id)
    if not inv: raise HTTPException(404, "Invoice not found")
    inv.status = InvoiceStatus(status); await db.commit()
    return {"id": str(inv.id), "status": inv.status.value}

# ── Expenses ────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    project_id: UUID | None = None; description: str; category: ExpenseCategory = ExpenseCategory.OTHER; amount: float; expense_date: str | None = None; receipt_ref: str | None = None; vendor_id: UUID | None = None

@router.get("/expenses")
async def list_expenses(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Expense).order_by(Expense.expense_date.desc())
    if project_id: q = q.where(Expense.project_id == project_id)
    result = await db.execute(q.limit(200))
    return [{"id": str(e.id), "description": e.description, "category": e.category.value, "amount": e.amount, "expense_date": e.expense_date.isoformat()[:10] if e.expense_date else None, "is_approved": e.is_approved} for e in result.scalars().all()]

@router.post("/expenses", status_code=201, dependencies=[Depends(require_permission("finance.expense.manage"))])
async def create_expense(p: ExpenseCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    e = Expense(project_id=p.project_id, user_id=current_user.id, vendor_id=p.vendor_id, description=p.description, category=p.category, amount=p.amount, expense_date=datetime.fromisoformat(p.expense_date) if p.expense_date else datetime.utcnow(), receipt_ref=p.receipt_ref)
    db.add(e); await db.commit(); await db.refresh(e)
    return {"id": str(e.id), "amount": e.amount}

@router.patch("/expenses/{expense_id}/approve", dependencies=[Depends(require_permission("finance.expense.manage"))])
async def approve_expense(expense_id: UUID, db: AsyncSession = Depends(get_db)):
    e = await db.get(Expense, expense_id)
    if not e: raise HTTPException(404, "Expense not found")
    e.is_approved = True; await db.commit()
    return {"id": str(e.id), "is_approved": True}

# ── Purchase Orders ─────────────────────────────────────────────────

class POCreate(BaseModel):
    project_id: UUID | None = None; vendor_id: UUID; po_number: str; description: str | None = None; total_amount: float = 0

@router.get("/purchase-orders")
async def list_pos(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
    if project_id: q = q.where(PurchaseOrder.project_id == project_id)
    result = await db.execute(q.limit(100))
    return [{"id": str(po.id), "po_number": po.po_number, "status": po.status.value, "total_amount": po.total_amount, "description": po.description} for po in result.scalars().all()]

@router.post("/purchase-orders", status_code=201, dependencies=[Depends(require_permission("finance.po.manage"))])
async def create_po(p: POCreate, db: AsyncSession = Depends(get_db)):
    po = PurchaseOrder(project_id=p.project_id, vendor_id=p.vendor_id, po_number=p.po_number, description=p.description, total_amount=p.total_amount)
    db.add(po); await db.commit(); await db.refresh(po)
    return {"id": str(po.id), "po_number": po.po_number}

@router.patch("/purchase-orders/{po_id}", dependencies=[Depends(require_permission("finance.po.manage"))])
async def update_po_status(po_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    po = await db.get(PurchaseOrder, po_id)
    if not po: raise HTTPException(404, "PO not found")
    po.status = POStatus(status); await db.commit()
    return {"id": str(po.id), "status": po.status.value}

# ── Assets ──────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    project_id: UUID | None = None; name: str; asset_tag: str | None = None; category: str | None = None; purchase_cost: float | None = None; current_value: float | None = None; assigned_to: str | None = None; location: str | None = None; notes: str | None = None

@router.get("/assets")
async def list_assets(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Asset).order_by(Asset.name)
    if project_id: q = q.where(Asset.project_id == project_id)
    result = await db.execute(q.limit(200))
    return [{"id": str(a.id), "name": a.name, "asset_tag": a.asset_tag, "category": a.category, "status": a.status.value, "purchase_cost": a.purchase_cost, "current_value": a.current_value, "assigned_to": a.assigned_to, "location": a.location} for a in result.scalars().all()]

@router.post("/assets", status_code=201, dependencies=[Depends(require_permission("finance.asset.manage"))])
async def create_asset(p: AssetCreate, db: AsyncSession = Depends(get_db)):
    a = Asset(**p.model_dump()); db.add(a); await db.commit(); await db.refresh(a)
    return {"id": str(a.id), "name": a.name}

@router.delete("/assets/{asset_id}", status_code=204, dependencies=[Depends(require_permission("finance.asset.manage"))])
async def delete_asset(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    a = await db.get(Asset, asset_id)
    if not a: raise HTTPException(404, "Asset not found")
    await db.delete(a); await db.commit()

# ── Financial Dashboard ─────────────────────────────────────────────

@router.get("/dashboard")
async def erp_dashboard(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    inv_q = select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.total), 0))
    exp_q = select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0))
    po_q = select(func.count(PurchaseOrder.id), func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
    asset_q = select(func.count(Asset.id), func.coalesce(func.sum(Asset.current_value), 0))
    if project_id:
        inv_q = inv_q.where(Invoice.project_id == project_id)
        exp_q = exp_q.where(Expense.project_id == project_id)
        po_q = po_q.where(PurchaseOrder.project_id == project_id)
        asset_q = asset_q.where(Asset.project_id == project_id)

    inv = (await db.execute(inv_q)).one()
    exp = (await db.execute(exp_q)).one()
    po = (await db.execute(po_q)).one()
    asset = (await db.execute(asset_q)).one()

    # Revenue (paid receivable invoices)
    rev_q = select(func.coalesce(func.sum(Invoice.total), 0)).where(Invoice.status == InvoiceStatus.PAID, Invoice.invoice_type == InvoiceType.RECEIVABLE)
    if project_id: rev_q = rev_q.where(Invoice.project_id == project_id)
    revenue = (await db.execute(rev_q)).scalar() or 0

    return {
        "invoices": {"count": inv[0], "total": round(inv[1], 2)},
        "expenses": {"count": exp[0], "total": round(exp[1], 2)},
        "purchase_orders": {"count": po[0], "total": round(po[1], 2)},
        "assets": {"count": asset[0], "total_value": round(asset[1], 2)},
        "revenue": round(revenue, 2),
        "profit": round(revenue - (exp[1] or 0), 2),
    }


# ── Budgets ─────────────────────────────────────────────────────────

class BudgetLineIn(BaseModel):
    account_id: UUID | None = None; category: ExpenseCategory | None = None
    label: str; planned_amount: float = 0.0

class BudgetCreate(BaseModel):
    project_id: UUID | None = None; name: str
    period_start: str | None = None; period_end: str | None = None
    notes: str | None = None; lines: list[BudgetLineIn] = []

@router.get("/budgets")
async def list_budgets(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Budget).order_by(Budget.created_at.desc())
    if project_id: q = q.where(Budget.project_id == project_id)
    result = await db.execute(q)
    return [{"id": str(b.id), "name": b.name, "total_amount": b.total_amount, "period_start": b.period_start.isoformat()[:10] if b.period_start else None, "period_end": b.period_end.isoformat()[:10] if b.period_end else None} for b in result.scalars().all()]

@router.post("/budgets", status_code=201, dependencies=[Depends(require_permission("finance.budget.manage"))])
async def create_budget(p: BudgetCreate, db: AsyncSession = Depends(get_db)):
    b = Budget(project_id=p.project_id, name=p.name, notes=p.notes,
               period_start=datetime.fromisoformat(p.period_start) if p.period_start else None,
               period_end=datetime.fromisoformat(p.period_end) if p.period_end else None,
               total_amount=sum(l.planned_amount for l in p.lines))
    db.add(b); await db.flush()
    for l in p.lines:
        db.add(BudgetLine(budget_id=b.id, account_id=l.account_id, category=l.category, label=l.label, planned_amount=l.planned_amount))
    await db.commit(); await db.refresh(b)
    return {"id": str(b.id), "name": b.name, "total_amount": b.total_amount}

@router.get("/budgets/{budget_id}/variance")
async def budget_variance(budget_id: UUID, db: AsyncSession = Depends(get_db)):
    b = await db.get(Budget, budget_id)
    if not b: raise HTTPException(404, "Budget not found")
    lines = (await db.execute(select(BudgetLine).where(BudgetLine.budget_id == budget_id))).scalars().all()
    out = []
    total_actual = 0.0
    for l in lines:
        q = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.project_id == b.project_id) if b.project_id else select(func.coalesce(func.sum(Expense.amount), 0))
        if l.category: q = q.where(Expense.category == l.category)
        if b.period_start: q = q.where(Expense.expense_date >= b.period_start)
        if b.period_end: q = q.where(Expense.expense_date <= b.period_end)
        actual = await db.scalar(q) or 0.0
        total_actual += actual
        variance = l.planned_amount - actual
        out.append({"line_id": str(l.id), "label": l.label, "category": l.category.value if l.category else None,
                    "planned": l.planned_amount, "actual": round(actual, 2),
                    "variance": round(variance, 2), "pct_used": round(actual / l.planned_amount * 100, 1) if l.planned_amount else 0})
    return {"budget_id": str(b.id), "total_planned": b.total_amount, "total_actual": round(total_actual, 2),
            "total_variance": round(b.total_amount - total_actual, 2), "lines": out}


# ── Currencies & FX ─────────────────────────────────────────────────

class CurrencyCreate(BaseModel):
    code: str; name: str; symbol: str | None = None

class FxRateCreate(BaseModel):
    base_code: str; quote_code: str; rate: float; rate_date: str | None = None

@router.get("/currencies")
async def list_currencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency).order_by(Currency.code))
    return [{"code": c.code, "name": c.name, "symbol": c.symbol} for c in result.scalars().all()]

@router.post("/currencies", status_code=201)
async def create_currency(p: CurrencyCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(Currency, p.code)
    if existing: raise HTTPException(400, "Currency code exists")
    c = Currency(code=p.code.upper(), name=p.name, symbol=p.symbol)
    db.add(c); await db.commit()
    return {"code": c.code, "name": c.name}

@router.get("/fx-rates")
async def list_fx_rates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FxRate).order_by(FxRate.rate_date.desc()).limit(200))
    return [{"id": str(r.id), "base_code": r.base_code, "quote_code": r.quote_code, "rate": r.rate, "rate_date": r.rate_date.isoformat()[:10] if r.rate_date else None} for r in result.scalars().all()]

@router.post("/fx-rates", status_code=201)
async def create_fx_rate(p: FxRateCreate, db: AsyncSession = Depends(get_db)):
    r = FxRate(base_code=p.base_code.upper(), quote_code=p.quote_code.upper(), rate=p.rate,
               rate_date=datetime.fromisoformat(p.rate_date) if p.rate_date else datetime.utcnow())
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

@router.get("/fx-convert")
async def fx_convert(amount: float, from_code: str, to_code: str, db: AsyncSession = Depends(get_db)):
    if from_code.upper() == to_code.upper(): return {"amount": amount, "rate": 1.0}
    r = await db.scalar(select(FxRate).where(FxRate.base_code == from_code.upper(), FxRate.quote_code == to_code.upper()).order_by(FxRate.rate_date.desc()))
    if not r: raise HTTPException(404, f"No FX rate for {from_code}->{to_code}")
    return {"amount": round(amount * r.rate, 2), "rate": r.rate, "as_of": r.rate_date.isoformat()[:10]}


# ── Payments & Aging ────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    invoice_id: UUID; amount: float; payment_date: str | None = None
    method: str | None = None; reference: str | None = None; notes: str | None = None

@router.get("/payments")
async def list_payments(invoice_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Payment).order_by(Payment.payment_date.desc()).limit(200)
    if invoice_id: q = q.where(Payment.invoice_id == invoice_id)
    result = await db.execute(q)
    return [{"id": str(p.id), "invoice_id": str(p.invoice_id), "amount": p.amount, "method": p.method, "reference": p.reference, "payment_date": p.payment_date.isoformat()[:10] if p.payment_date else None} for p in result.scalars().all()]

@router.post("/payments", status_code=201, dependencies=[Depends(require_permission("finance.payment.record"))])
async def create_payment(p: PaymentCreate, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Invoice, p.invoice_id)
    if not inv: raise HTTPException(404, "Invoice not found")
    pay = Payment(invoice_id=p.invoice_id, amount=p.amount, method=p.method, reference=p.reference, notes=p.notes,
                  payment_date=datetime.fromisoformat(p.payment_date) if p.payment_date else datetime.utcnow())
    db.add(pay)
    inv.paid_amount = round((inv.paid_amount or 0) + p.amount, 2)
    if inv.paid_amount >= inv.total:
        inv.status = InvoiceStatus.PAID
    await db.commit(); await db.refresh(pay)
    return {"id": str(pay.id), "invoice_paid_amount": inv.paid_amount, "invoice_status": inv.status.value}

@router.get("/invoices/aging")
async def invoice_aging(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    q = select(Invoice).where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]))
    if project_id: q = q.where(Invoice.project_id == project_id)
    result = await db.execute(q)
    buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
    details = []
    for i in result.scalars().all():
        outstanding = (i.total or 0) - (i.paid_amount or 0)
        if outstanding <= 0: continue
        if not i.due_date:
            buckets["current"] += outstanding
            bucket = "current"
        else:
            days = (now - i.due_date.replace(tzinfo=None)).days
            if days <= 0: bucket = "current"
            elif days <= 30: bucket = "1_30"
            elif days <= 60: bucket = "31_60"
            elif days <= 90: bucket = "61_90"
            else: bucket = "over_90"
            buckets[bucket] += outstanding
        details.append({"id": str(i.id), "invoice_number": i.invoice_number, "outstanding": round(outstanding, 2), "bucket": bucket, "due_date": i.due_date.isoformat()[:10] if i.due_date else None})
    return {"buckets": {k: round(v, 2) for k, v in buckets.items()}, "invoices": details}


# ── Recurring Invoices ──────────────────────────────────────────────

class RecurringInvoiceCreate(BaseModel):
    project_id: UUID | None = None; vendor_id: UUID | None = None
    template_name: str; invoice_type: InvoiceType = InvoiceType.RECEIVABLE
    amount: float = 0.0; tax_rate: float = 0.0
    frequency: RecurringFrequency = RecurringFrequency.MONTHLY
    next_run: str | None = None; description: str | None = None

@router.get("/recurring-invoices")
async def list_recurring(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecurringInvoice).order_by(RecurringInvoice.next_run))
    return [{"id": str(r.id), "template_name": r.template_name, "amount": r.amount, "frequency": r.frequency.value, "next_run": r.next_run.isoformat()[:10] if r.next_run else None, "is_active": r.is_active} for r in result.scalars().all()]

@router.post("/recurring-invoices", status_code=201)
async def create_recurring(p: RecurringInvoiceCreate, db: AsyncSession = Depends(get_db)):
    r = RecurringInvoice(project_id=p.project_id, vendor_id=p.vendor_id, template_name=p.template_name,
                         invoice_type=p.invoice_type, amount=p.amount, tax_rate=p.tax_rate, frequency=p.frequency,
                         description=p.description,
                         next_run=datetime.fromisoformat(p.next_run) if p.next_run else datetime.utcnow())
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

def _advance(dt: datetime, freq: RecurringFrequency) -> datetime:
    if freq == RecurringFrequency.WEEKLY: return dt + timedelta(weeks=1)
    if freq == RecurringFrequency.MONTHLY: return dt + timedelta(days=30)
    if freq == RecurringFrequency.QUARTERLY: return dt + timedelta(days=91)
    return dt + timedelta(days=365)

@router.post("/recurring-invoices/run")
async def run_recurring(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    due = (await db.execute(select(RecurringInvoice).where(RecurringInvoice.is_active == True, RecurringInvoice.next_run <= now))).scalars().all()
    generated = []
    for r in due:
        tax_amount = r.amount * r.tax_rate / 100
        inv = Invoice(project_id=r.project_id, vendor_id=r.vendor_id,
                      invoice_number=f"REC-{r.template_name[:10]}-{int(now.timestamp())}",
                      invoice_type=r.invoice_type, subtotal=r.amount, tax_rate=r.tax_rate,
                      tax_amount=round(tax_amount, 2), total=round(r.amount + tax_amount, 2),
                      notes=f"Auto-generated from recurring '{r.template_name}'")
        db.add(inv)
        r.last_generated = now
        r.next_run = _advance(r.next_run, r.frequency)
        generated.append(r.template_name)
    await db.commit()
    return {"generated": generated, "count": len(generated)}


# ── Tax Report ──────────────────────────────────────────────────────

@router.get("/reports/tax")
async def tax_report(start: str | None = None, end: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Invoice).where(Invoice.status == InvoiceStatus.PAID)
    if start: q = q.where(Invoice.issue_date >= datetime.fromisoformat(start))
    if end: q = q.where(Invoice.issue_date <= datetime.fromisoformat(end))
    invs = (await db.execute(q)).scalars().all()
    collected = sum(i.tax_amount or 0 for i in invs if i.invoice_type == InvoiceType.RECEIVABLE)
    paid = sum(i.tax_amount or 0 for i in invs if i.invoice_type == InvoiceType.PAYABLE)
    by_rate: dict[float, dict] = {}
    for i in invs:
        r = round(i.tax_rate or 0, 2)
        b = by_rate.setdefault(r, {"rate": r, "taxable": 0.0, "tax": 0.0})
        b["taxable"] += i.subtotal or 0
        b["tax"] += i.tax_amount or 0
    return {"collected": round(collected, 2), "paid": round(paid, 2), "net_owed": round(collected - paid, 2),
            "by_rate": [{"rate": v["rate"], "taxable": round(v["taxable"], 2), "tax": round(v["tax"], 2)} for v in by_rate.values()]}


# ── Journal & Trial Balance ─────────────────────────────────────────

class JournalLineIn(BaseModel):
    account_id: UUID; debit: float = 0.0; credit: float = 0.0; description: str | None = None

class JournalEntryCreate(BaseModel):
    entry_number: str; entry_date: str | None = None; memo: str | None = None
    lines: list[JournalLineIn]

@router.get("/journal")
async def list_journal(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JournalEntry).order_by(JournalEntry.entry_date.desc()).limit(100))
    return [{"id": str(j.id), "entry_number": j.entry_number, "entry_date": j.entry_date.isoformat()[:10] if j.entry_date else None, "memo": j.memo, "is_posted": j.is_posted} for j in result.scalars().all()]

@router.post("/journal", status_code=201, dependencies=[Depends(require_permission("finance.journal.post"))])
async def create_journal(p: JournalEntryCreate, db: AsyncSession = Depends(get_db)):
    total_d = sum(l.debit for l in p.lines)
    total_c = sum(l.credit for l in p.lines)
    if round(total_d, 2) != round(total_c, 2):
        raise HTTPException(400, f"Debits ({total_d}) must equal credits ({total_c})")
    je = JournalEntry(entry_number=p.entry_number, memo=p.memo,
                     entry_date=datetime.fromisoformat(p.entry_date) if p.entry_date else datetime.utcnow())
    db.add(je); await db.flush()
    for l in p.lines:
        db.add(JournalLine(entry_id=je.id, account_id=l.account_id, debit=l.debit, credit=l.credit, description=l.description))
    await db.commit()
    return {"id": str(je.id), "entry_number": je.entry_number}

@router.post("/journal/{entry_id}/post", dependencies=[Depends(require_permission("finance.journal.post"))])
async def post_journal(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    je = await db.get(JournalEntry, entry_id)
    if not je: raise HTTPException(404, "Entry not found")
    if je.is_posted: return {"id": str(je.id), "is_posted": True}
    lines = (await db.execute(select(JournalLine).where(JournalLine.entry_id == entry_id))).scalars().all()
    for l in lines:
        acc = await db.get(Account, l.account_id)
        if not acc: continue
        if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            acc.balance = (acc.balance or 0) + l.debit - l.credit
        else:
            acc.balance = (acc.balance or 0) + l.credit - l.debit
    je.is_posted = True
    await db.commit()
    return {"id": str(je.id), "is_posted": True}

@router.get("/reports/trial-balance")
async def trial_balance(db: AsyncSession = Depends(get_db)):
    accs = (await db.execute(select(Account).where(Account.is_active == True).order_by(Account.code))).scalars().all()
    rows = []
    total_d = total_c = 0.0
    for a in accs:
        bal = a.balance or 0
        if a.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            debit, credit = (bal, 0) if bal >= 0 else (0, -bal)
        else:
            debit, credit = (0, bal) if bal >= 0 else (-bal, 0)
        total_d += debit; total_c += credit
        rows.append({"code": a.code, "name": a.name, "account_type": a.account_type.value, "debit": round(debit, 2), "credit": round(credit, 2)})
    return {"rows": rows, "total_debit": round(total_d, 2), "total_credit": round(total_c, 2), "balanced": round(total_d, 2) == round(total_c, 2)}


# ── Bank Reconciliation ─────────────────────────────────────────────

class BankTxnCreate(BaseModel):
    account_id: UUID | None = None; txn_date: str | None = None
    description: str; amount: float; reference: str | None = None

@router.get("/bank-transactions")
async def list_bank_txns(reconciled: bool | None = None, db: AsyncSession = Depends(get_db)):
    q = select(BankTransaction).order_by(BankTransaction.txn_date.desc()).limit(200)
    if reconciled is not None: q = q.where(BankTransaction.is_reconciled == reconciled)
    result = await db.execute(q)
    return [{"id": str(t.id), "description": t.description, "amount": t.amount, "reference": t.reference, "txn_date": t.txn_date.isoformat()[:10] if t.txn_date else None, "is_reconciled": t.is_reconciled, "matched_invoice_id": str(t.matched_invoice_id) if t.matched_invoice_id else None} for t in result.scalars().all()]

@router.post("/bank-transactions", status_code=201, dependencies=[Depends(require_permission("finance.bank.manage"))])
async def create_bank_txn(p: BankTxnCreate, db: AsyncSession = Depends(get_db)):
    t = BankTransaction(account_id=p.account_id, description=p.description, amount=p.amount, reference=p.reference,
                        txn_date=datetime.fromisoformat(p.txn_date) if p.txn_date else datetime.utcnow())
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id": str(t.id)}

@router.post("/bank-transactions/{txn_id}/match")
async def match_bank_txn(txn_id: UUID, invoice_id: UUID | None = None, expense_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    t = await db.get(BankTransaction, txn_id)
    if not t: raise HTTPException(404, "Transaction not found")
    t.matched_invoice_id = invoice_id
    t.matched_expense_id = expense_id
    t.is_reconciled = bool(invoice_id or expense_id)
    await db.commit()
    return {"id": str(t.id), "is_reconciled": t.is_reconciled}

@router.post("/bank-transactions/auto-match")
async def auto_match(tolerance: float = 0.01, db: AsyncSession = Depends(get_db)):
    unmatched = (await db.execute(select(BankTransaction).where(BankTransaction.is_reconciled == False))).scalars().all()
    matched = 0
    for t in unmatched:
        q = select(Invoice).where(Invoice.status != InvoiceStatus.CANCELLED, func.abs(Invoice.total - abs(t.amount)) < tolerance).limit(1)
        inv = (await db.execute(q)).scalar_one_or_none()
        if inv:
            t.matched_invoice_id = inv.id; t.is_reconciled = True; matched += 1
    await db.commit()
    return {"matched": matched, "remaining": len(unmatched) - matched}


# ── Inventory ───────────────────────────────────────────────────────

class WarehouseCreate(BaseModel):
    code: str; name: str; address: str | None = None

class ProductCreate(BaseModel):
    sku: str; name: str; description: str | None = None
    unit_cost: float = 0.0; unit_price: float = 0.0
    reorder_point: int = 0; reorder_qty: int = 0

class StockMovementCreate(BaseModel):
    product_id: UUID; warehouse_id: UUID; movement_type: MovementType
    quantity: float; unit_cost: float | None = None; reference: str | None = None; notes: str | None = None

@router.get("/warehouses")
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Warehouse).order_by(Warehouse.code))
    return [{"id": str(w.id), "code": w.code, "name": w.name, "address": w.address, "is_active": w.is_active} for w in result.scalars().all()]

@router.post("/warehouses", status_code=201, dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def create_warehouse(p: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    w = Warehouse(**p.model_dump())
    db.add(w); await db.commit(); await db.refresh(w)
    return {"id": str(w.id), "code": w.code}

@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).order_by(Product.sku).limit(500))
    return [{"id": str(p.id), "sku": p.sku, "name": p.name, "unit_cost": p.unit_cost, "unit_price": p.unit_price, "reorder_point": p.reorder_point, "reorder_qty": p.reorder_qty, "is_active": p.is_active} for p in result.scalars().all()]

@router.post("/products", status_code=201, dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def create_product(p: ProductCreate, db: AsyncSession = Depends(get_db)):
    pr = Product(**p.model_dump())
    db.add(pr); await db.commit(); await db.refresh(pr)
    return {"id": str(pr.id), "sku": pr.sku}

@router.get("/stock")
async def stock_levels(warehouse_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    signed_qty = case(
        (StockMovement.movement_type == MovementType.RECEIPT, StockMovement.quantity),
        (StockMovement.movement_type == MovementType.ISSUE, -StockMovement.quantity),
        (StockMovement.movement_type == MovementType.ADJUST, StockMovement.quantity),
        else_=0,
    )
    q = select(
        StockMovement.product_id, StockMovement.warehouse_id, func.sum(signed_qty).label("qty"),
    ).group_by(StockMovement.product_id, StockMovement.warehouse_id)
    if warehouse_id: q = q.where(StockMovement.warehouse_id == warehouse_id)
    rows = (await db.execute(q)).all()
    products = {str(p.id): p for p in (await db.execute(select(Product))).scalars().all()}
    warehouses = {str(w.id): w for w in (await db.execute(select(Warehouse))).scalars().all()}
    out = []
    for pid, wid, qty in rows:
        p = products.get(str(pid)); w = warehouses.get(str(wid))
        if not p or not w: continue
        out.append({"product_id": str(pid), "sku": p.sku, "name": p.name, "warehouse_id": str(wid), "warehouse": w.code,
                    "quantity": round(qty or 0, 2), "below_reorder": (qty or 0) <= p.reorder_point})
    return out

@router.post("/stock/movements", status_code=201, dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def create_movement(p: StockMovementCreate, db: AsyncSession = Depends(get_db)):
    m = StockMovement(**p.model_dump())
    db.add(m); await db.commit(); await db.refresh(m)
    return {"id": str(m.id)}

@router.get("/stock/reorder")
async def reorder_report(db: AsyncSession = Depends(get_db)):
    levels = await stock_levels(None, db)
    return [l for l in levels if l["below_reorder"]]


# ── Depreciation ────────────────────────────────────────────────────

class DepScheduleCreate(BaseModel):
    asset_id: UUID; method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    useful_life_months: int; salvage_value: float = 0.0; rate: float | None = None
    start_date: str

@router.get("/depreciation")
async def list_dep(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DepreciationSchedule))
    return [{"id": str(d.id), "asset_id": str(d.asset_id), "method": d.method.value, "useful_life_months": d.useful_life_months, "salvage_value": d.salvage_value, "accumulated": d.accumulated, "start_date": d.start_date.isoformat()[:10] if d.start_date else None, "last_run": d.last_run.isoformat()[:10] if d.last_run else None} for d in result.scalars().all()]

@router.post("/depreciation", status_code=201)
async def create_dep(p: DepScheduleCreate, db: AsyncSession = Depends(get_db)):
    d = DepreciationSchedule(asset_id=p.asset_id, method=p.method, useful_life_months=p.useful_life_months,
                             salvage_value=p.salvage_value, rate=p.rate,
                             start_date=datetime.fromisoformat(p.start_date))
    db.add(d); await db.commit(); await db.refresh(d)
    return {"id": str(d.id)}

@router.post("/depreciation/run")
async def run_depreciation(as_of: str | None = None, db: AsyncSession = Depends(get_db)):
    now = datetime.fromisoformat(as_of) if as_of else datetime.utcnow()
    schedules = (await db.execute(select(DepreciationSchedule))).scalars().all()
    posted = 0
    total = 0.0
    for s in schedules:
        asset = await db.get(Asset, s.asset_id)
        if not asset or not asset.purchase_cost: continue
        last = s.last_run or s.start_date
        months_since = max(0, int((now - last).days / 30))
        if months_since == 0: continue
        depreciable = asset.purchase_cost - s.salvage_value
        if s.method == DepreciationMethod.STRAIGHT_LINE:
            monthly = depreciable / s.useful_life_months
        else:
            rate = s.rate or (2 / s.useful_life_months)
            nbv = asset.purchase_cost - s.accumulated
            monthly = nbv * rate / 12
        charge = round(monthly * months_since, 2)
        if s.accumulated + charge > depreciable:
            charge = max(0, round(depreciable - s.accumulated, 2))
        s.accumulated = round((s.accumulated or 0) + charge, 2)
        s.last_run = now
        asset.current_value = round(asset.purchase_cost - s.accumulated, 2)
        total += charge
        posted += 1
    await db.commit()
    return {"schedules_posted": posted, "total_depreciation": round(total, 2), "as_of": now.isoformat()[:10]}


# ── Credit Notes ────────────────────────────────────────────────────

class CreditNoteCreate(BaseModel):
    invoice_id: UUID; cn_number: str; amount: float; reason: str | None = None

@router.get("/credit-notes")
async def list_credit_notes(invoice_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(CreditNote).order_by(CreditNote.issued_date.desc()).limit(200)
    if invoice_id: q = q.where(CreditNote.invoice_id == invoice_id)
    result = await db.execute(q)
    return [{"id": str(c.id), "invoice_id": str(c.invoice_id), "cn_number": c.cn_number, "amount": c.amount, "reason": c.reason, "issued_date": c.issued_date.isoformat()[:10] if c.issued_date else None} for c in result.scalars().all()]

@router.post("/credit-notes", status_code=201)
async def create_credit_note(p: CreditNoteCreate, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Invoice, p.invoice_id)
    if not inv: raise HTTPException(404, "Invoice not found")
    if p.amount <= 0: raise HTTPException(400, "Amount must be positive")
    if p.amount > inv.total: raise HTTPException(400, "Credit exceeds invoice total")
    cn = CreditNote(invoice_id=p.invoice_id, cn_number=p.cn_number, amount=p.amount, reason=p.reason)
    db.add(cn)
    # Reduce paid requirement: credit reduces outstanding
    inv.paid_amount = round((inv.paid_amount or 0) + p.amount, 2)
    if inv.paid_amount >= inv.total:
        inv.status = InvoiceStatus.PAID
    await db.commit(); await db.refresh(cn)
    return {"id": str(cn.id), "cn_number": cn.cn_number}


# ── Financial Statements ────────────────────────────────────────────

@router.get("/reports/pnl")
async def pnl_report(start: str | None = None, end: str | None = None, db: AsyncSession = Depends(get_db)):
    accs = (await db.execute(select(Account).where(Account.account_type.in_([AccountType.REVENUE, AccountType.EXPENSE])))).scalars().all()
    revenue = sum(a.balance or 0 for a in accs if a.account_type == AccountType.REVENUE)
    expenses = sum(a.balance or 0 for a in accs if a.account_type == AccountType.EXPENSE)
    # Also pull invoice/expense actuals for period if provided
    if start or end:
        q_rev = select(func.coalesce(func.sum(Invoice.total), 0)).where(Invoice.status == InvoiceStatus.PAID, Invoice.invoice_type == InvoiceType.RECEIVABLE)
        q_exp = select(func.coalesce(func.sum(Expense.amount), 0))
        if start:
            q_rev = q_rev.where(Invoice.issue_date >= datetime.fromisoformat(start))
            q_exp = q_exp.where(Expense.expense_date >= datetime.fromisoformat(start))
        if end:
            q_rev = q_rev.where(Invoice.issue_date <= datetime.fromisoformat(end))
            q_exp = q_exp.where(Expense.expense_date <= datetime.fromisoformat(end))
        revenue = float(await db.scalar(q_rev) or 0)
        expenses = float(await db.scalar(q_exp) or 0)
    return {"revenue": round(revenue, 2), "expenses": round(expenses, 2),
            "net_income": round(revenue - expenses, 2),
            "accounts": [{"code": a.code, "name": a.name, "type": a.account_type.value, "balance": a.balance} for a in accs]}

@router.get("/reports/balance-sheet")
async def balance_sheet(db: AsyncSession = Depends(get_db)):
    accs = (await db.execute(select(Account).where(Account.is_active == True).order_by(Account.code))).scalars().all()
    assets = [a for a in accs if a.account_type == AccountType.ASSET]
    liabs = [a for a in accs if a.account_type == AccountType.LIABILITY]
    equity = [a for a in accs if a.account_type == AccountType.EQUITY]
    return {
        "assets": [{"code": a.code, "name": a.name, "balance": a.balance or 0} for a in assets],
        "liabilities": [{"code": a.code, "name": a.name, "balance": a.balance or 0} for a in liabs],
        "equity": [{"code": a.code, "name": a.name, "balance": a.balance or 0} for a in equity],
        "total_assets": round(sum(a.balance or 0 for a in assets), 2),
        "total_liabilities": round(sum(a.balance or 0 for a in liabs), 2),
        "total_equity": round(sum(a.balance or 0 for a in equity), 2),
    }


# ── Cash Flow Forecast ──────────────────────────────────────────────

@router.get("/reports/cash-flow")
async def cash_flow(days: int = 90, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    horizon = now + timedelta(days=days)
    # Inflows: unpaid receivable invoices due in window
    inv_q = select(Invoice).where(Invoice.invoice_type == InvoiceType.RECEIVABLE,
                                   Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
                                   Invoice.due_date.isnot(None), Invoice.due_date <= horizon)
    inflows = [{"date": i.due_date.isoformat()[:10], "amount": round((i.total or 0) - (i.paid_amount or 0), 2), "label": f"Inv {i.invoice_number}"}
               for i in (await db.execute(inv_q)).scalars().all()]
    # Outflows: unpaid payable invoices + recurring upcoming + expenses projection
    out_q = select(Invoice).where(Invoice.invoice_type == InvoiceType.PAYABLE,
                                   Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
                                   Invoice.due_date.isnot(None), Invoice.due_date <= horizon)
    outflows = [{"date": i.due_date.isoformat()[:10], "amount": -round((i.total or 0) - (i.paid_amount or 0), 2), "label": f"Pay {i.invoice_number}"}
                for i in (await db.execute(out_q)).scalars().all()]
    # Recurring outflows (payable templates only for simplicity)
    rec_q = select(RecurringInvoice).where(RecurringInvoice.is_active == True, RecurringInvoice.next_run <= horizon)
    for r in (await db.execute(rec_q)).scalars().all():
        sign = -1 if r.invoice_type == InvoiceType.PAYABLE else 1
        amt = round(r.amount * (1 + r.tax_rate / 100), 2) * sign
        outflows.append({"date": r.next_run.isoformat()[:10], "amount": amt, "label": f"Rec {r.template_name}"})
    events = sorted(inflows + outflows, key=lambda e: e["date"])
    cumulative = 0.0
    for e in events:
        cumulative += e["amount"]; e["running"] = round(cumulative, 2)
    return {"horizon_days": days, "total_inflow": round(sum(e["amount"] for e in inflows), 2),
            "total_outflow": round(sum(e["amount"] for e in outflows), 2),
            "net": round(sum(e["amount"] for e in events), 2), "events": events}


# ── Requisitions ────────────────────────────────────────────────────

class RequisitionItemIn(BaseModel):
    product_id: UUID | None = None; description: str; quantity: float = 1.0; unit_price: float = 0.0

class RequisitionCreate(BaseModel):
    project_id: UUID | None = None; req_number: str
    justification: str | None = None; needed_by: str | None = None
    items: list[RequisitionItemIn] = []

@router.get("/requisitions")
async def list_requisitions(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Requisition).order_by(Requisition.created_at.desc()).limit(200)
    if status: q = q.where(Requisition.status == RequisitionStatus(status))
    result = await db.execute(q)
    return [{"id": str(r.id), "req_number": r.req_number, "status": r.status.value, "estimated_amount": r.estimated_amount, "needed_by": r.needed_by.isoformat()[:10] if r.needed_by else None, "converted_po_id": str(r.converted_po_id) if r.converted_po_id else None} for r in result.scalars().all()]

@router.post("/requisitions", status_code=201, dependencies=[Depends(require_permission("finance.requisition.manage"))])
async def create_requisition(p: RequisitionCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = sum((i.quantity or 1) * (i.unit_price or 0) for i in p.items)
    r = Requisition(project_id=p.project_id, requester_id=current_user.id, req_number=p.req_number,
                    justification=p.justification, estimated_amount=round(total, 2),
                    needed_by=datetime.fromisoformat(p.needed_by) if p.needed_by else None)
    db.add(r); await db.flush()
    for it in p.items:
        db.add(RequisitionItem(req_id=r.id, product_id=it.product_id, description=it.description, quantity=it.quantity, unit_price=it.unit_price))
    await db.commit(); await db.refresh(r)
    return {"id": str(r.id), "req_number": r.req_number, "estimated_amount": r.estimated_amount}

@router.patch("/requisitions/{req_id}", dependencies=[Depends(require_permission("finance.requisition.manage"))])
async def update_requisition_status(req_id: UUID, status: str = Query(...), db: AsyncSession = Depends(get_db)):
    r = await db.get(Requisition, req_id)
    if not r: raise HTTPException(404, "Not found")
    r.status = RequisitionStatus(status); await db.commit()
    return {"id": str(r.id), "status": r.status.value}

class RequisitionConvert(BaseModel):
    vendor_id: UUID; po_number: str | None = None

@router.post("/requisitions/{req_id}/convert", dependencies=[Depends(require_permission("finance.requisition.manage"))])
async def convert_requisition(req_id: UUID, p: RequisitionConvert, db: AsyncSession = Depends(get_db)):
    r = await db.get(Requisition, req_id)
    if not r: raise HTTPException(404, "Not found")
    if r.status != RequisitionStatus.APPROVED: raise HTTPException(400, "Only approved requisitions can convert")
    if r.converted_po_id: raise HTTPException(400, "Already converted")
    po = PurchaseOrder(project_id=r.project_id, vendor_id=p.vendor_id,
                       po_number=p.po_number or f"PO-FROM-{r.req_number}",
                       description=f"From requisition {r.req_number}",
                       total_amount=r.estimated_amount)
    db.add(po); await db.flush()
    r.converted_po_id = po.id
    r.status = RequisitionStatus.CONVERTED
    await db.commit()
    return {"req_id": str(r.id), "po_id": str(po.id), "po_number": po.po_number}
