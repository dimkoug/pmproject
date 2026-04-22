"""ERP System: Accounts, Invoices, Expenses, Vendors, Purchase Orders, Assets, Budgets, Payments, Journal, FX, Bank Recon."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import Float, String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.erp import (
    Account, AccountType, Invoice, InvoiceItem, InvoiceStatus, InvoiceType,
    Expense, ExpenseCategory, Vendor, PurchaseOrder, PurchaseOrderLine, POStatus, Asset, AssetStatus,
    Budget, BudgetLine, Currency, FxRate, Payment, RecurringInvoice, RecurringFrequency,
    JournalEntry, JournalLine, BankTransaction,
    Warehouse, Product, StockMovement, MovementType,
    DepreciationSchedule, DepreciationMethod, CreditNote,
    Requisition, RequisitionItem, RequisitionStatus,
    SalesOrder, SalesOrderLine, SalesOrderStatus,
    GoodsReceipt, GrnLine, GrnStatus,
    Rfq, RfqLine, RfqVendor, RfqStatus,
    SupplierQuote, SupplierQuoteLine, SupplierQuoteStatus,
    StockBatch, StockSerial, SerialStatus,
    CostCenter, ProfitCenter,
)
from app.models.crm import Quote, QuoteItem, QuoteStatus

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
async def list_vendors(
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    q = select(Vendor).order_by(Vendor.name)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Vendor.workspace_id == ws_id) | (Vendor.workspace_id.is_(None)))
    result = await db.execute(q)
    return [{"id": str(v.id), "name": v.name, "contact_person": v.contact_person, "email": v.email, "phone": v.phone, "is_active": v.is_active} for v in result.scalars().all()]

@router.post("/vendors", status_code=201, dependencies=[Depends(require_permission("finance.vendor.manage"))])
async def create_vendor(
    p: VendorCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    ws_id = await get_active_workspace_id(request, current_user, db)
    v = Vendor(**p.model_dump(), workspace_id=ws_id)
    db.add(v); await db.commit(); await db.refresh(v)
    return {"id": str(v.id), "name": v.name}

@router.delete("/vendors/{vendor_id}", status_code=204, dependencies=[Depends(require_permission("finance.vendor.manage"))])
async def delete_vendor(vendor_id: UUID, db: AsyncSession = Depends(get_db)):
    v = await db.get(Vendor, vendor_id)
    if not v: raise HTTPException(404, "Vendor not found")
    await db.delete(v); await db.commit()


@router.get("/vendors/{vendor_id}/performance")
async def vendor_performance(vendor_id: UUID, db: AsyncSession = Depends(get_db)):
    """Aggregate POs for this vendor into performance KPIs (#4):
      * on_time_rate  = (POs received on/before delivery_date) / (POs received)
      * avg_days_late = mean(received_date - delivery_date) for late ones
      * defect_rate   = mean of per-PO defect_rate values (nulls ignored)
      * total_spend   = sum of total_amount on non-cancelled POs
    """
    v = await db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    pos = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.vendor_id == vendor_id)
    )).scalars().all()
    received = [p for p in pos if p.received_date is not None]
    on_time = [p for p in received if p.delivery_date and p.received_date and p.received_date <= p.delivery_date]
    late = [p for p in received if p.delivery_date and p.received_date and p.received_date > p.delivery_date]
    avg_days_late = (
        sum((p.received_date - p.delivery_date).days for p in late) / len(late)
        if late else 0.0
    )
    defects = [p.defect_rate for p in pos if p.defect_rate is not None]
    total_spend = sum(p.total_amount or 0.0 for p in pos if p.status != POStatus.DRAFT)
    return {
        "vendor_id": str(v.id), "name": v.name,
        "po_count": len(pos),
        "received_count": len(received),
        "on_time_rate": (len(on_time) / len(received)) if received else None,
        "avg_days_late": round(avg_days_late, 2),
        "defect_rate": (sum(defects) / len(defects)) if defects else None,
        "total_spend": round(total_spend, 2),
    }


class POReceiveIn(BaseModel):
    received_date: str | None = None  # ISO datetime; defaults to now
    defect_rate: float | None = None


@router.post("/purchase-orders/{po_id}/receive", dependencies=[Depends(require_permission("finance.po.manage"))])
async def receive_purchase_order(po_id: UUID, p: POReceiveIn, db: AsyncSession = Depends(get_db)):
    """Mark a PO as received, recording the date + optional QC defect rate
    (0..1). Drives the vendor performance aggregates above."""
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    from datetime import datetime as _dt
    po.received_date = _dt.fromisoformat(p.received_date) if p.received_date else _dt.utcnow()
    if p.defect_rate is not None:
        if not (0.0 <= p.defect_rate <= 1.0):
            raise HTTPException(400, "defect_rate must be between 0 and 1")
        po.defect_rate = p.defect_rate
    await db.commit()
    return {"id": str(po.id), "received_date": po.received_date.isoformat()}


# ── Invoices ────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    project_id: UUID | None = None; vendor_id: UUID | None = None; invoice_number: str
    invoice_type: InvoiceType = InvoiceType.RECEIVABLE; due_date: str | None = None
    subtotal: float = 0; tax_rate: float = 0; notes: str | None = None
    items: list[dict] = []

@router.get("/invoices")
async def list_invoices(
    request: Request,
    project_id: UUID | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    q = select(Invoice).order_by(Invoice.created_at.desc())
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Invoice.workspace_id == ws_id) | (Invoice.workspace_id.is_(None)))
    if project_id: q = q.where(Invoice.project_id == project_id)
    result = await db.execute(q.limit(100))
    return [{"id": str(i.id), "invoice_number": i.invoice_number, "invoice_type": i.invoice_type.value, "status": i.status.value, "total": i.total, "issue_date": i.issue_date.isoformat()[:10] if i.issue_date else None, "due_date": i.due_date.isoformat()[:10] if i.due_date else None} for i in result.scalars().all()]

@router.post("/invoices", status_code=201, dependencies=[Depends(require_permission("finance.invoice.create"))])
async def create_invoice(
    p: InvoiceCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    from app.services.workspaces import get_active_workspace_id
    ws_id = await get_active_workspace_id(request, current_user, db)
    tax_amount = p.subtotal * p.tax_rate / 100
    inv = Invoice(project_id=p.project_id, vendor_id=p.vendor_id, invoice_number=p.invoice_number, invoice_type=p.invoice_type, subtotal=p.subtotal, tax_rate=p.tax_rate, tax_amount=round(tax_amount, 2), total=round(p.subtotal + tax_amount, 2), notes=p.notes, due_date=datetime.fromisoformat(p.due_date) if p.due_date else None, workspace_id=ws_id)
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


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    """Render the invoice as a branded PDF (#1) and stream it inline."""
    from fastapi.responses import Response
    from app.models.crm import Company
    from app.services.pdf_docs import render_invoice_pdf

    inv = await db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    items = (await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
    )).scalars().all()
    customer = None
    if inv.company_id:
        c = await db.get(Company, inv.company_id)
        if c:
            customer = {"name": c.name, "address": getattr(c, "address", None) or ""}
    pdf_bytes = render_invoice_pdf(
        invoice={
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.issue_date,
            "due_date": inv.due_date,
            "status": inv.status.value if inv.status else None,
            "subtotal": inv.subtotal, "tax_amount": inv.tax_amount, "total_amount": inv.total,
            "notes": inv.notes,
        },
        lines=[{"description": i.description, "quantity": i.quantity,
                "unit_price": i.unit_price, "amount": i.amount} for i in items],
        customer=customer,
        company=None,
        currency=(inv.currency or "USD"),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{inv.invoice_number}.pdf"'},
    )


@router.get("/quotes/{quote_id}/pdf")
async def download_quote_pdf(quote_id: UUID, db: AsyncSession = Depends(get_db)):
    """Render the quote as a branded PDF (#1)."""
    from fastapi.responses import Response
    from app.models.crm import Company
    from app.services.pdf_docs import render_quote_pdf

    q = await db.get(Quote, quote_id)
    if not q:
        raise HTTPException(404, "Quote not found")
    items = (await db.execute(
        select(QuoteItem).where(QuoteItem.quote_id == quote_id)
    )).scalars().all()
    customer = None
    if q.company_id:
        c = await db.get(Company, q.company_id)
        if c:
            customer = {"name": c.name, "address": getattr(c, "address", None) or ""}
    tax_amount = round((q.subtotal or 0.0) * (q.tax_rate or 0.0), 2)
    pdf_bytes = render_quote_pdf(
        quote={
            "quote_number": q.quote_number,
            "valid_until": q.valid_until,
            "status": q.status.value if q.status else None,
            "subtotal": q.subtotal, "tax_amount": tax_amount, "total_amount": q.total,
            "terms": q.notes,
        },
        lines=[{"description": i.description, "quantity": i.quantity,
                "unit_price": i.unit_price, "amount": i.amount} for i in items],
        customer=customer,
        company=None,
        currency=getattr(q, "currency", None) or "USD",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="quote-{q.quote_number}.pdf"'},
    )

# ── Expenses ────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    project_id: UUID | None = None; description: str; category: ExpenseCategory = ExpenseCategory.OTHER; amount: float; expense_date: str | None = None; receipt_ref: str | None = None; vendor_id: UUID | None = None

@router.get("/expenses")
async def list_expenses(
    request: Request,
    project_id: UUID | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    q = select(Expense).order_by(Expense.expense_date.desc())
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Expense.workspace_id == ws_id) | (Expense.workspace_id.is_(None)))
    if project_id: q = q.where(Expense.project_id == project_id)
    result = await db.execute(q.limit(200))
    return [{"id": str(e.id), "description": e.description, "category": e.category.value, "amount": e.amount, "expense_date": e.expense_date.isoformat()[:10] if e.expense_date else None, "is_approved": e.is_approved} for e in result.scalars().all()]

@router.post("/expenses", status_code=201, dependencies=[Depends(require_permission("finance.expense.manage"))])
async def create_expense(
    p: ExpenseCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    from app.services.workspaces import get_active_workspace_id
    ws_id = await get_active_workspace_id(request, current_user, db)
    e = Expense(project_id=p.project_id, user_id=current_user.id, vendor_id=p.vendor_id, description=p.description, category=p.category, amount=p.amount, expense_date=datetime.fromisoformat(p.expense_date) if p.expense_date else datetime.now(timezone.utc), receipt_ref=p.receipt_ref, workspace_id=ws_id)
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
async def list_pos(
    request: Request,
    project_id: UUID | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    q = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((PurchaseOrder.workspace_id == ws_id) | (PurchaseOrder.workspace_id.is_(None)))
    if project_id: q = q.where(PurchaseOrder.project_id == project_id)
    result = await db.execute(q.limit(100))
    return [{"id": str(po.id), "po_number": po.po_number, "status": po.status.value, "total_amount": po.total_amount, "description": po.description} for po in result.scalars().all()]

@router.post("/purchase-orders", status_code=201, dependencies=[Depends(require_permission("finance.po.manage"))])
async def create_po(
    p: POCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    ws_id = await get_active_workspace_id(request, current_user, db)
    po = PurchaseOrder(project_id=p.project_id, vendor_id=p.vendor_id, po_number=p.po_number, description=p.description, total_amount=p.total_amount, workspace_id=ws_id)
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
async def list_assets(
    request: Request,
    project_id: UUID | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    q = select(Asset).order_by(Asset.name)
    ws_id = await get_active_workspace_id(request, current_user, db)
    if ws_id is not None:
        q = q.where((Asset.workspace_id == ws_id) | (Asset.workspace_id.is_(None)))
    if project_id: q = q.where(Asset.project_id == project_id)
    result = await db.execute(q.limit(200))
    return [{"id": str(a.id), "name": a.name, "asset_tag": a.asset_tag, "category": a.category, "status": a.status.value, "purchase_cost": a.purchase_cost, "current_value": a.current_value, "assigned_to": a.assigned_to, "location": a.location} for a in result.scalars().all()]

@router.post("/assets", status_code=201, dependencies=[Depends(require_permission("finance.asset.manage"))])
async def create_asset(
    p: AssetCreate,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspaces import get_active_workspace_id
    ws_id = await get_active_workspace_id(request, current_user, db)
    a = Asset(**p.model_dump(), workspace_id=ws_id); db.add(a); await db.commit(); await db.refresh(a)
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
               rate_date=datetime.fromisoformat(p.rate_date) if p.rate_date else datetime.now(timezone.utc))
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
                  payment_date=datetime.fromisoformat(p.payment_date) if p.payment_date else datetime.now(timezone.utc))
    db.add(pay)
    inv.paid_amount = round((inv.paid_amount or 0) + p.amount, 2)
    if inv.paid_amount >= inv.total:
        inv.status = InvoiceStatus.PAID
    await db.commit(); await db.refresh(pay)
    return {"id": str(pay.id), "invoice_paid_amount": inv.paid_amount, "invoice_status": inv.status.value}

@router.get("/invoices/aging")
async def invoice_aging(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
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
                         next_run=datetime.fromisoformat(p.next_run) if p.next_run else datetime.now(timezone.utc))
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

def _advance(dt: datetime, freq: RecurringFrequency) -> datetime:
    if freq == RecurringFrequency.WEEKLY: return dt + timedelta(weeks=1)
    if freq == RecurringFrequency.MONTHLY: return dt + timedelta(days=30)
    if freq == RecurringFrequency.QUARTERLY: return dt + timedelta(days=91)
    return dt + timedelta(days=365)

@router.post("/recurring-invoices/run")
async def run_recurring(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
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
    account_id: UUID
    debit: float = 0.0
    credit: float = 0.0
    description: str | None = None
    cost_center_id: UUID | None = None
    profit_center_id: UUID | None = None

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
                     entry_date=datetime.fromisoformat(p.entry_date) if p.entry_date else datetime.now(timezone.utc))
    db.add(je); await db.flush()
    for l in p.lines:
        db.add(JournalLine(
            entry_id=je.id, account_id=l.account_id, debit=l.debit, credit=l.credit, description=l.description,
            cost_center_id=l.cost_center_id, profit_center_id=l.profit_center_id,
        ))
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

def _bank_txn_dict(t: BankTransaction) -> dict:
    return {
        "id": str(t.id),
        "account_id": str(t.account_id) if t.account_id else None,
        "description": t.description,
        "amount": t.amount,
        "reference": t.reference,
        "txn_date": t.txn_date.isoformat()[:10] if t.txn_date else None,
        "is_reconciled": t.is_reconciled,
        "matched_invoice_id": str(t.matched_invoice_id) if t.matched_invoice_id else None,
        "matched_expense_id": str(t.matched_expense_id) if t.matched_expense_id else None,
        "matched_journal_entry_id": str(t.matched_journal_entry_id) if t.matched_journal_entry_id else None,
        "notes": t.notes,
    }


@router.get("/bank-transactions")
async def list_bank_txns(
    reconciled: bool | None = None,
    account_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(BankTransaction).order_by(BankTransaction.txn_date.desc()).limit(500)
    if reconciled is not None:
        q = q.where(BankTransaction.is_reconciled == reconciled)
    if account_id:
        q = q.where(BankTransaction.account_id == account_id)
    result = await db.execute(q)
    return [_bank_txn_dict(t) for t in result.scalars().all()]

@router.post("/bank-transactions", status_code=201, dependencies=[Depends(require_permission("finance.bank.manage"))])
async def create_bank_txn(p: BankTxnCreate, db: AsyncSession = Depends(get_db)):
    t = BankTransaction(account_id=p.account_id, description=p.description, amount=p.amount, reference=p.reference,
                        txn_date=datetime.fromisoformat(p.txn_date) if p.txn_date else datetime.now(timezone.utc))
    db.add(t); await db.commit(); await db.refresh(t)
    return _bank_txn_dict(t)


class BankMatchRequest(BaseModel):
    invoice_id: UUID | None = None
    expense_id: UUID | None = None
    journal_entry_id: UUID | None = None


@router.post("/bank-transactions/{txn_id}/match", dependencies=[Depends(require_permission("finance.bank.manage"))])
async def match_bank_txn(txn_id: UUID, p: BankMatchRequest, db: AsyncSession = Depends(get_db)):
    t = await db.get(BankTransaction, txn_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    if not (p.invoice_id or p.expense_id or p.journal_entry_id):
        raise HTTPException(400, "Provide at least one match target")
    t.matched_invoice_id = p.invoice_id
    t.matched_expense_id = p.expense_id
    t.matched_journal_entry_id = p.journal_entry_id
    t.is_reconciled = True
    await db.commit()
    return _bank_txn_dict(t)


@router.delete("/bank-transactions/{txn_id}/match", dependencies=[Depends(require_permission("finance.bank.manage"))])
async def unmatch_bank_txn(txn_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await db.get(BankTransaction, txn_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    t.matched_invoice_id = None
    t.matched_expense_id = None
    t.matched_journal_entry_id = None
    t.is_reconciled = False
    await db.commit()
    return _bank_txn_dict(t)


class BankCreateJournalRequest(BaseModel):
    debit_account_id: UUID
    credit_account_id: UUID
    memo: str | None = None
    entry_number: str | None = None


@router.post("/bank-transactions/{txn_id}/create-journal", dependencies=[Depends(require_permission("finance.journal.post"))])
async def create_journal_from_bank_txn(txn_id: UUID, p: BankCreateJournalRequest, db: AsyncSession = Depends(get_db)):
    """Convenience: turn an unmatched bank txn into a posted journal entry and link them."""
    t = await db.get(BankTransaction, txn_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    if t.is_reconciled:
        raise HTTPException(400, "Transaction is already reconciled — unmatch first")
    amt = abs(t.amount)
    je = JournalEntry(
        entry_number=p.entry_number or f"JE-BANK-{str(t.id)[:8]}",
        memo=p.memo or f"From bank txn: {t.description}",
        is_posted=True,
    )
    db.add(je)
    await db.flush()
    db.add(JournalLine(entry_id=je.id, account_id=p.debit_account_id, debit=amt, credit=0.0, description=t.description))
    db.add(JournalLine(entry_id=je.id, account_id=p.credit_account_id, debit=0.0, credit=amt, description=t.description))
    t.matched_journal_entry_id = je.id
    t.is_reconciled = True
    await db.commit()
    return {"bank_txn_id": str(t.id), "journal_entry_id": str(je.id), "entry_number": je.entry_number}


@router.post("/bank-transactions/auto-match", dependencies=[Depends(require_permission("finance.bank.manage"))])
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


# ── Warehouse bins (#5) ────────────────────────────────────────────

class BinIn(BaseModel):
    warehouse_id: UUID
    code: str
    description: str | None = None


@router.get("/warehouses/{warehouse_id}/bins")
async def list_bins(warehouse_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models.erp import WarehouseBin
    rows = (await db.execute(
        select(WarehouseBin).where(WarehouseBin.warehouse_id == warehouse_id)
        .order_by(WarehouseBin.code)
    )).scalars().all()
    return [{"id": str(b.id), "code": b.code, "description": b.description, "is_active": b.is_active} for b in rows]


@router.post("/warehouse-bins", status_code=201,
             dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def create_bin(p: BinIn, db: AsyncSession = Depends(get_db)):
    from app.models.erp import WarehouseBin
    b = WarehouseBin(warehouse_id=p.warehouse_id, code=p.code, description=p.description)
    db.add(b); await db.commit(); await db.refresh(b)
    return {"id": str(b.id), "code": b.code}


# ── Barcode lookup (#5) ────────────────────────────────────────────

@router.get("/products/by-barcode/{code}",
            dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def product_by_barcode(code: str, db: AsyncSession = Depends(get_db)):
    """Resolve a scanned barcode to a product record. Gated behind
    `finance.inventory.manage` because the response body leaks `unit_cost`
    — which is sensitive pricing info that shouldn't be readable by every
    authenticated user."""
    from app.services.inventory import scan_barcode
    p = await scan_barcode(db, code)
    if not p:
        raise HTTPException(404, "Unknown barcode")
    return {"id": str(p.id), "sku": p.sku, "barcode": p.barcode, "name": p.name,
            "unit_price": p.unit_price, "unit_cost": p.unit_cost}


# ── FIFO issue (#5) ────────────────────────────────────────────────

class FifoIssueIn(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    quantity: float
    reference: str | None = None
    bin_id: UUID | None = None
    notes: str | None = None


@router.post("/stock/fifo-issue",
             dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def fifo_issue(p: FifoIssueIn, db: AsyncSession = Depends(get_db)):
    """Issue stock using FIFO batch consumption. Returns the per-batch
    breakdown so downstream accounting can compute weighted cost."""
    from app.services.inventory import issue_fifo
    consumed = await issue_fifo(
        db, p.product_id, p.warehouse_id, p.quantity,
        reference=p.reference, bin_id=p.bin_id, notes=p.notes,
    )
    total_cost = sum((c.get("qty_taken") or 0.0) * (c.get("unit_cost") or 0.0) for c in consumed)
    return {"consumed": consumed, "total_cost": round(total_cost, 4)}

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
    now = datetime.fromisoformat(as_of) if as_of else datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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


# ── Sales Orders (Quote → SO → Invoice) ─────────────────────────────

class SalesOrderLineIn(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0


class SalesOrderCreate(BaseModel):
    order_number: str
    quote_id: UUID | None = None
    company_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    delivery_date: str | None = None
    tax_rate: float = 0.0
    currency: str = "USD"
    notes: str | None = None
    lines: list[SalesOrderLineIn] = []


def _so_summary(so: SalesOrder) -> dict:
    return {
        "id": str(so.id),
        "order_number": so.order_number,
        "status": so.status.value,
        "quote_id": str(so.quote_id) if so.quote_id else None,
        "company_id": str(so.company_id) if so.company_id else None,
        "opportunity_id": str(so.opportunity_id) if so.opportunity_id else None,
        "project_id": str(so.project_id) if so.project_id else None,
        "invoice_id": str(so.invoice_id) if so.invoice_id else None,
        "order_date": so.order_date.isoformat()[:10] if so.order_date else None,
        "delivery_date": so.delivery_date.isoformat()[:10] if so.delivery_date else None,
        "subtotal": so.subtotal,
        "tax_rate": so.tax_rate,
        "tax_amount": so.tax_amount,
        "total": so.total,
        "currency": so.currency,
        "notes": so.notes,
    }


@router.get("/sales-orders")
async def list_sales_orders(
    status: str | None = None,
    company_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SalesOrder).order_by(SalesOrder.created_at.desc()).limit(200)
    if status:
        q = q.where(SalesOrder.status == SalesOrderStatus(status))
    if company_id:
        q = q.where(SalesOrder.company_id == company_id)
    result = await db.execute(q)
    return [_so_summary(so) for so in result.scalars().all()]


@router.get("/sales-orders/{order_id}")
async def get_sales_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    so = await db.get(SalesOrder, order_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    lines_q = await db.execute(select(SalesOrderLine).where(SalesOrderLine.order_id == so.id))
    lines = [{
        "id": str(ln.id),
        "product_id": str(ln.product_id) if ln.product_id else None,
        "description": ln.description,
        "quantity": ln.quantity,
        "unit_price": ln.unit_price,
        "amount": ln.amount,
    } for ln in lines_q.scalars().all()]
    out = _so_summary(so)
    out["lines"] = lines
    return out


@router.post("/sales-orders", status_code=201, dependencies=[Depends(require_permission("sales.order.manage"))])
async def create_sales_order(p: SalesOrderCreate, db: AsyncSession = Depends(get_db)):
    subtotal = round(sum((ln.quantity or 1) * (ln.unit_price or 0) for ln in p.lines), 2)
    tax_amount = round(subtotal * p.tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    so = SalesOrder(
        order_number=p.order_number,
        quote_id=p.quote_id,
        company_id=p.company_id,
        opportunity_id=p.opportunity_id,
        project_id=p.project_id,
        delivery_date=datetime.fromisoformat(p.delivery_date) if p.delivery_date else None,
        subtotal=subtotal,
        tax_rate=p.tax_rate,
        tax_amount=tax_amount,
        total=total,
        currency=p.currency,
        notes=p.notes,
    )
    db.add(so)
    await db.flush()
    for ln in p.lines:
        amt = round((ln.quantity or 1) * (ln.unit_price or 0), 2)
        db.add(SalesOrderLine(
            order_id=so.id,
            product_id=ln.product_id,
            description=ln.description,
            quantity=ln.quantity,
            unit_price=ln.unit_price,
            amount=amt,
        ))
    await db.commit()
    await db.refresh(so)
    return _so_summary(so)


@router.post("/sales-orders/from-quote/{quote_id}", status_code=201, dependencies=[Depends(require_permission("sales.order.manage"))])
async def create_sales_order_from_quote(quote_id: UUID, order_number: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    quote = await db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    items_q = await db.execute(select(QuoteItem).where(QuoteItem.quote_id == quote.id))
    items = items_q.scalars().all()
    if not items:
        raise HTTPException(400, "Quote has no line items")
    so = SalesOrder(
        order_number=order_number or f"SO-FROM-{quote.quote_number}",
        quote_id=quote.id,
        company_id=quote.company_id,
        opportunity_id=quote.opportunity_id,
        subtotal=quote.subtotal,
        tax_rate=quote.tax_rate,
        tax_amount=round(quote.subtotal * quote.tax_rate / 100, 2),
        total=quote.total,
        notes=quote.notes,
    )
    db.add(so)
    await db.flush()
    for item in items:
        db.add(SalesOrderLine(
            order_id=so.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount,
        ))
    quote.status = QuoteStatus.CONVERTED
    await db.commit()
    await db.refresh(so)
    return _so_summary(so)


class SalesOrderStatusUpdate(BaseModel):
    status: SalesOrderStatus


@router.patch("/sales-orders/{order_id}/status", dependencies=[Depends(require_permission("sales.order.manage"))])
async def update_sales_order_status(order_id: UUID, p: SalesOrderStatusUpdate, db: AsyncSession = Depends(get_db)):
    so = await db.get(SalesOrder, order_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    so.status = p.status
    await db.commit()
    return {"id": str(so.id), "status": so.status.value}


@router.post("/sales-orders/{order_id}/invoice", dependencies=[Depends(require_permission("sales.order.manage"))])
async def invoice_sales_order(order_id: UUID, invoice_number: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    so = await db.get(SalesOrder, order_id)
    if not so:
        raise HTTPException(404, "Sales order not found")
    if so.invoice_id:
        raise HTTPException(400, "Sales order already invoiced")
    lines_q = await db.execute(select(SalesOrderLine).where(SalesOrderLine.order_id == so.id))
    lines = lines_q.scalars().all()
    if not lines:
        raise HTTPException(400, "Sales order has no lines")
    inv = Invoice(
        project_id=so.project_id,
        invoice_number=invoice_number or f"INV-FROM-{so.order_number}",
        invoice_type=InvoiceType.RECEIVABLE,
        subtotal=so.subtotal,
        tax_rate=so.tax_rate,
        tax_amount=so.tax_amount,
        total=so.total,
        currency=so.currency,
        notes=f"From sales order {so.order_number}",
    )
    db.add(inv)
    await db.flush()
    for ln in lines:
        db.add(InvoiceItem(
            invoice_id=inv.id,
            description=ln.description,
            quantity=ln.quantity,
            unit_price=ln.unit_price,
            amount=ln.amount,
        ))
    so.invoice_id = inv.id
    so.status = SalesOrderStatus.INVOICED
    await db.commit()
    await db.refresh(inv)
    return {"sales_order_id": str(so.id), "invoice_id": str(inv.id), "invoice_number": inv.invoice_number}


# ── Purchase Order Lines (needed for GRN) ───────────────────────────

class POLineIn(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0


@router.get("/purchase-orders/{po_id}")
async def get_po(po_id: UUID, db: AsyncSession = Depends(get_db)):
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    lines_q = await db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id))
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "vendor_id": str(po.vendor_id),
        "project_id": str(po.project_id) if po.project_id else None,
        "status": po.status.value,
        "description": po.description,
        "total_amount": po.total_amount,
        "order_date": po.order_date.isoformat()[:10] if po.order_date else None,
        "delivery_date": po.delivery_date.isoformat()[:10] if po.delivery_date else None,
        "lines": [{
            "id": str(ln.id),
            "product_id": str(ln.product_id) if ln.product_id else None,
            "description": ln.description,
            "quantity": ln.quantity,
            "unit_price": ln.unit_price,
            "quantity_received": ln.quantity_received,
            "amount": ln.amount,
            "outstanding": round(ln.quantity - ln.quantity_received, 4),
        } for ln in lines_q.scalars().all()],
    }


@router.post("/purchase-orders/{po_id}/lines", status_code=201, dependencies=[Depends(require_permission("finance.po.manage"))])
async def add_po_line(po_id: UUID, p: POLineIn, db: AsyncSession = Depends(get_db)):
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    amt = round((p.quantity or 1) * (p.unit_price or 0), 2)
    ln = PurchaseOrderLine(
        po_id=po.id,
        product_id=p.product_id,
        description=p.description,
        quantity=p.quantity,
        unit_price=p.unit_price,
        amount=amt,
    )
    db.add(ln)
    po.total_amount = round(po.total_amount + amt, 2)
    await db.commit()
    await db.refresh(ln)
    return {"id": str(ln.id), "amount": ln.amount}


# ── Goods Receipt Notes (GRN) ───────────────────────────────────────

class GrnLineIn(BaseModel):
    po_line_id: UUID | None = None
    product_id: UUID | None = None
    description: str
    quantity_received: float
    notes: str | None = None


class GrnCreate(BaseModel):
    grn_number: str
    po_id: UUID
    warehouse_id: UUID | None = None
    received_date: str | None = None
    notes: str | None = None
    lines: list[GrnLineIn] = []


@router.get("/goods-receipts")
async def list_grns(
    po_id: UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(GoodsReceipt).order_by(GoodsReceipt.created_at.desc()).limit(200)
    if po_id:
        q = q.where(GoodsReceipt.po_id == po_id)
    if status:
        q = q.where(GoodsReceipt.status == GrnStatus(status))
    result = await db.execute(q)
    return [{
        "id": str(g.id),
        "grn_number": g.grn_number,
        "po_id": str(g.po_id),
        "warehouse_id": str(g.warehouse_id) if g.warehouse_id else None,
        "status": g.status.value,
        "received_date": g.received_date.isoformat()[:10] if g.received_date else None,
        "notes": g.notes,
    } for g in result.scalars().all()]


@router.get("/goods-receipts/{grn_id}")
async def get_grn(grn_id: UUID, db: AsyncSession = Depends(get_db)):
    g = await db.get(GoodsReceipt, grn_id)
    if not g:
        raise HTTPException(404, "GRN not found")
    lines_q = await db.execute(select(GrnLine).where(GrnLine.grn_id == g.id))
    return {
        "id": str(g.id),
        "grn_number": g.grn_number,
        "po_id": str(g.po_id),
        "warehouse_id": str(g.warehouse_id) if g.warehouse_id else None,
        "status": g.status.value,
        "received_date": g.received_date.isoformat() if g.received_date else None,
        "notes": g.notes,
        "lines": [{
            "id": str(ln.id),
            "po_line_id": str(ln.po_line_id) if ln.po_line_id else None,
            "product_id": str(ln.product_id) if ln.product_id else None,
            "description": ln.description,
            "quantity_received": ln.quantity_received,
            "notes": ln.notes,
        } for ln in lines_q.scalars().all()],
    }


@router.post("/goods-receipts", status_code=201, dependencies=[Depends(require_permission("finance.grn.manage"))])
async def create_grn(p: GrnCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    po = await db.get(PurchaseOrder, p.po_id)
    if not po:
        raise HTTPException(404, "PO not found")
    # Validate quantities against PO line outstanding
    po_lines_q = await db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id))
    po_lines = {ln.id: ln for ln in po_lines_q.scalars().all()}
    for ln in p.lines:
        if ln.po_line_id:
            po_line = po_lines.get(ln.po_line_id)
            if not po_line:
                raise HTTPException(400, f"PO line {ln.po_line_id} not part of PO")
            outstanding = po_line.quantity - po_line.quantity_received
            if ln.quantity_received > outstanding + 1e-6:
                raise HTTPException(400, f"Received qty {ln.quantity_received} exceeds outstanding {outstanding} for '{po_line.description}'")
    grn = GoodsReceipt(
        grn_number=p.grn_number,
        po_id=p.po_id,
        warehouse_id=p.warehouse_id,
        received_date=datetime.fromisoformat(p.received_date) if p.received_date else datetime.now(timezone.utc),
        received_by_user_id=current_user.id,
        notes=p.notes,
    )
    db.add(grn)
    await db.flush()
    for ln in p.lines:
        db.add(GrnLine(
            grn_id=grn.id,
            po_line_id=ln.po_line_id,
            product_id=ln.product_id,
            description=ln.description,
            quantity_received=ln.quantity_received,
            notes=ln.notes,
        ))
    await db.commit()
    await db.refresh(grn)
    return {"id": str(grn.id), "grn_number": grn.grn_number, "status": grn.status.value}


@router.post("/goods-receipts/{grn_id}/confirm", dependencies=[Depends(require_permission("finance.grn.manage"))])
async def confirm_grn(grn_id: UUID, db: AsyncSession = Depends(get_db)):
    grn = await db.get(GoodsReceipt, grn_id)
    if not grn:
        raise HTTPException(404, "GRN not found")
    if grn.status != GrnStatus.DRAFT:
        raise HTTPException(400, f"GRN is already {grn.status.value}")
    if not grn.warehouse_id:
        raise HTTPException(400, "GRN needs a warehouse to confirm (creates stock movements)")
    lines_q = await db.execute(select(GrnLine).where(GrnLine.grn_id == grn.id))
    grn_lines = lines_q.scalars().all()
    if not grn_lines:
        raise HTTPException(400, "GRN has no lines")
    # Write inbound stock movements + bump PO line received quantities
    for ln in grn_lines:
        if ln.product_id:
            db.add(StockMovement(
                product_id=ln.product_id,
                warehouse_id=grn.warehouse_id,
                movement_type=MovementType.RECEIPT,
                quantity=ln.quantity_received,
                reference=f"GRN {grn.grn_number}",
                notes=f"Receipt against PO (grn={grn.id})",
            ))
        if ln.po_line_id:
            po_line = await db.get(PurchaseOrderLine, ln.po_line_id)
            if po_line:
                po_line.quantity_received = round(po_line.quantity_received + ln.quantity_received, 4)
    # Bump PO status if everything received
    po = await db.get(PurchaseOrder, grn.po_id)
    if po:
        po_lines_q = await db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id))
        po_lines = po_lines_q.scalars().all()
        if po_lines and all(ln.quantity_received >= ln.quantity - 1e-6 for ln in po_lines):
            po.status = POStatus.RECEIVED
    grn.status = GrnStatus.CONFIRMED
    await db.commit()
    return {"id": str(grn.id), "status": grn.status.value}


# ── RFQs / Supplier Quotes ──────────────────────────────────────────

class RfqLineIn(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    target_price: float | None = None


class RfqCreate(BaseModel):
    rfq_number: str
    requisition_id: UUID | None = None
    project_id: UUID | None = None
    response_due_date: str | None = None
    notes: str | None = None
    lines: list[RfqLineIn] = []
    vendor_ids: list[UUID] = []


@router.get("/rfqs")
async def list_rfqs(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Rfq).order_by(Rfq.created_at.desc()).limit(200)
    if status:
        q = q.where(Rfq.status == RfqStatus(status))
    result = await db.execute(q)
    return [{
        "id": str(r.id),
        "rfq_number": r.rfq_number,
        "status": r.status.value,
        "requisition_id": str(r.requisition_id) if r.requisition_id else None,
        "issued_date": r.issued_date.isoformat()[:10] if r.issued_date else None,
        "response_due_date": r.response_due_date.isoformat()[:10] if r.response_due_date else None,
        "awarded_po_id": str(r.awarded_po_id) if r.awarded_po_id else None,
    } for r in result.scalars().all()]


@router.get("/rfqs/{rfq_id}")
async def get_rfq(rfq_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await db.get(Rfq, rfq_id)
    if not r:
        raise HTTPException(404, "RFQ not found")
    lines_q = await db.execute(select(RfqLine).where(RfqLine.rfq_id == r.id))
    vendors_q = await db.execute(select(RfqVendor).where(RfqVendor.rfq_id == r.id))
    return {
        "id": str(r.id),
        "rfq_number": r.rfq_number,
        "status": r.status.value,
        "requisition_id": str(r.requisition_id) if r.requisition_id else None,
        "project_id": str(r.project_id) if r.project_id else None,
        "issued_date": r.issued_date.isoformat() if r.issued_date else None,
        "response_due_date": r.response_due_date.isoformat() if r.response_due_date else None,
        "awarded_po_id": str(r.awarded_po_id) if r.awarded_po_id else None,
        "notes": r.notes,
        "lines": [{
            "id": str(ln.id),
            "product_id": str(ln.product_id) if ln.product_id else None,
            "description": ln.description,
            "quantity": ln.quantity,
            "target_price": ln.target_price,
        } for ln in lines_q.scalars().all()],
        "vendors": [{
            "id": str(v.id),
            "vendor_id": str(v.vendor_id),
            "sent_at": v.sent_at.isoformat() if v.sent_at else None,
            "responded_at": v.responded_at.isoformat() if v.responded_at else None,
        } for v in vendors_q.scalars().all()],
    }


@router.post("/rfqs", status_code=201, dependencies=[Depends(require_permission("finance.rfq.manage"))])
async def create_rfq(p: RfqCreate, db: AsyncSession = Depends(get_db)):
    r = Rfq(
        rfq_number=p.rfq_number,
        requisition_id=p.requisition_id,
        project_id=p.project_id,
        response_due_date=datetime.fromisoformat(p.response_due_date) if p.response_due_date else None,
        notes=p.notes,
    )
    db.add(r)
    await db.flush()
    for ln in p.lines:
        db.add(RfqLine(rfq_id=r.id, product_id=ln.product_id, description=ln.description, quantity=ln.quantity, target_price=ln.target_price))
    for vid in p.vendor_ids:
        db.add(RfqVendor(rfq_id=r.id, vendor_id=vid))
    await db.commit()
    await db.refresh(r)
    return {"id": str(r.id), "rfq_number": r.rfq_number}


@router.post("/rfqs/{rfq_id}/send", dependencies=[Depends(require_permission("finance.rfq.manage"))])
async def send_rfq(rfq_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await db.get(Rfq, rfq_id)
    if not r:
        raise HTTPException(404, "RFQ not found")
    if r.status != RfqStatus.DRAFT:
        raise HTTPException(400, f"RFQ is {r.status.value}, cannot send")
    now = datetime.now(timezone.utc)
    vendors_q = await db.execute(select(RfqVendor).where(RfqVendor.rfq_id == r.id, RfqVendor.sent_at.is_(None)))
    for v in vendors_q.scalars().all():
        v.sent_at = now
    r.issued_date = now
    r.status = RfqStatus.SENT
    await db.commit()
    return {"id": str(r.id), "status": r.status.value}


class SupplierQuoteLineIn(BaseModel):
    rfq_line_id: UUID
    unit_price: float = 0.0
    lead_time_days: int | None = None
    notes: str | None = None


class SupplierQuoteCreate(BaseModel):
    vendor_id: UUID
    currency: str = "USD"
    lead_time_days: int | None = None
    terms: str | None = None
    valid_until: str | None = None
    lines: list[SupplierQuoteLineIn] = []


@router.get("/rfqs/{rfq_id}/quotes")
async def list_supplier_quotes(rfq_id: UUID, db: AsyncSession = Depends(get_db)):
    sq_q = await db.execute(select(SupplierQuote).where(SupplierQuote.rfq_id == rfq_id).order_by(SupplierQuote.total))
    quotes = sq_q.scalars().all()
    if not quotes:
        return []
    # Batch-load all lines in a single round-trip, then group by quote.
    quote_ids = [sq.id for sq in quotes]
    lines_q = await db.execute(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id.in_(quote_ids)))
    lines_by_quote: dict = {qid: [] for qid in quote_ids}
    for ln in lines_q.scalars().all():
        lines_by_quote[ln.supplier_quote_id].append(ln)
    out = []
    for sq in quotes:
        out.append({
            "id": str(sq.id),
            "vendor_id": str(sq.vendor_id),
            "status": sq.status.value,
            "total": sq.total,
            "currency": sq.currency,
            "lead_time_days": sq.lead_time_days,
            "terms": sq.terms,
            "valid_until": sq.valid_until.isoformat()[:10] if sq.valid_until else None,
            "submitted_at": sq.submitted_at.isoformat() if sq.submitted_at else None,
            "lines": [{
                "id": str(ln.id),
                "rfq_line_id": str(ln.rfq_line_id),
                "unit_price": ln.unit_price,
                "lead_time_days": ln.lead_time_days,
                "notes": ln.notes,
            } for ln in lines_by_quote[sq.id]],
        })
    return out


@router.post("/rfqs/{rfq_id}/quotes", status_code=201, dependencies=[Depends(require_permission("finance.rfq.manage"))])
async def submit_supplier_quote(rfq_id: UUID, p: SupplierQuoteCreate, db: AsyncSession = Depends(get_db)):
    r = await db.get(Rfq, rfq_id)
    if not r:
        raise HTTPException(404, "RFQ not found")
    # Validate all rfq_line_ids belong to this RFQ
    rfq_lines_q = await db.execute(select(RfqLine).where(RfqLine.rfq_id == r.id))
    rfq_lines = {ln.id: ln for ln in rfq_lines_q.scalars().all()}
    total = 0.0
    for ln in p.lines:
        if ln.rfq_line_id not in rfq_lines:
            raise HTTPException(400, f"RFQ line {ln.rfq_line_id} not part of RFQ")
        total += (rfq_lines[ln.rfq_line_id].quantity or 1) * (ln.unit_price or 0)
    sq = SupplierQuote(
        rfq_id=r.id,
        vendor_id=p.vendor_id,
        total=round(total, 2),
        currency=p.currency,
        lead_time_days=p.lead_time_days,
        terms=p.terms,
        valid_until=datetime.fromisoformat(p.valid_until) if p.valid_until else None,
    )
    db.add(sq)
    await db.flush()
    for ln in p.lines:
        db.add(SupplierQuoteLine(
            supplier_quote_id=sq.id,
            rfq_line_id=ln.rfq_line_id,
            unit_price=ln.unit_price,
            lead_time_days=ln.lead_time_days,
            notes=ln.notes,
        ))
    # Mark the RfqVendor.responded_at
    vendor_link_q = await db.execute(select(RfqVendor).where(RfqVendor.rfq_id == r.id, RfqVendor.vendor_id == p.vendor_id))
    vendor_link = vendor_link_q.scalar_one_or_none()
    if vendor_link:
        vendor_link.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sq)
    return {"id": str(sq.id), "total": sq.total}


class RfqAward(BaseModel):
    supplier_quote_id: UUID
    po_number: str | None = None


@router.post("/rfqs/{rfq_id}/award", dependencies=[Depends(require_permission("finance.rfq.manage"))])
async def award_rfq(rfq_id: UUID, p: RfqAward, db: AsyncSession = Depends(get_db)):
    r = await db.get(Rfq, rfq_id)
    if not r:
        raise HTTPException(404, "RFQ not found")
    if r.awarded_po_id:
        raise HTTPException(400, "RFQ already awarded")
    sq = await db.get(SupplierQuote, p.supplier_quote_id)
    if not sq or sq.rfq_id != r.id:
        raise HTTPException(400, "Supplier quote not part of this RFQ")
    # Create PO + PO lines from winning quote
    po = PurchaseOrder(
        project_id=r.project_id,
        vendor_id=sq.vendor_id,
        po_number=p.po_number or f"PO-FROM-{r.rfq_number}",
        description=f"Awarded from RFQ {r.rfq_number}",
        total_amount=sq.total,
        status=POStatus.APPROVED,
    )
    db.add(po)
    await db.flush()
    # Copy lines: use RFQ line qty + supplier quote unit_price
    sq_lines_q = await db.execute(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id == sq.id))
    for sl in sq_lines_q.scalars().all():
        rl = await db.get(RfqLine, sl.rfq_line_id)
        if not rl:
            continue
        db.add(PurchaseOrderLine(
            po_id=po.id,
            product_id=rl.product_id,
            description=rl.description,
            quantity=rl.quantity,
            unit_price=sl.unit_price,
            amount=round(rl.quantity * sl.unit_price, 2),
        ))
    # Flag winner / losers + close RFQ
    sq.status = SupplierQuoteStatus.WON
    other_q = await db.execute(select(SupplierQuote).where(SupplierQuote.rfq_id == r.id, SupplierQuote.id != sq.id))
    for other in other_q.scalars().all():
        other.status = SupplierQuoteStatus.LOST
    r.awarded_quote_id = sq.id
    r.awarded_po_id = po.id
    r.status = RfqStatus.AWARDED
    await db.commit()
    return {"rfq_id": str(r.id), "po_id": str(po.id), "po_number": po.po_number}


# ── Product tracking flags (batch/serial opt-in) ────────────────────

class ProductTrackingUpdate(BaseModel):
    track_batch: bool | None = None
    track_serial: bool | None = None


@router.patch("/products/{product_id}/tracking", dependencies=[Depends(require_permission("finance.inventory.manage"))])
async def update_product_tracking(product_id: UUID, p: ProductTrackingUpdate, db: AsyncSession = Depends(get_db)):
    prod = await db.get(Product, product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    if p.track_batch is not None:
        prod.track_batch = p.track_batch
    if p.track_serial is not None:
        prod.track_serial = p.track_serial
    await db.commit()
    return {"id": str(prod.id), "track_batch": prod.track_batch, "track_serial": prod.track_serial}


# ── Batches / Lots ──────────────────────────────────────────────────

class BatchCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    batch_code: str
    mfg_date: str | None = None
    expiry_date: str | None = None
    qty_received: float = 0.0
    cost_per_unit: float | None = None
    notes: str | None = None


def _batch_dict(b: StockBatch) -> dict:
    return {
        "id": str(b.id),
        "product_id": str(b.product_id),
        "warehouse_id": str(b.warehouse_id) if b.warehouse_id else None,
        "batch_code": b.batch_code,
        "mfg_date": b.mfg_date.isoformat()[:10] if b.mfg_date else None,
        "expiry_date": b.expiry_date.isoformat()[:10] if b.expiry_date else None,
        "qty_received": b.qty_received,
        "qty_on_hand": b.qty_on_hand,
        "cost_per_unit": b.cost_per_unit,
        "notes": b.notes,
    }


@router.get("/batches")
async def list_batches(
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    expiring_within_days: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(StockBatch).order_by(StockBatch.expiry_date.asc().nulls_last(), StockBatch.created_at.desc()).limit(500)
    if product_id:
        q = q.where(StockBatch.product_id == product_id)
    if warehouse_id:
        q = q.where(StockBatch.warehouse_id == warehouse_id)
    if expiring_within_days is not None and expiring_within_days >= 0:
        cutoff = datetime.now(timezone.utc) + timedelta(days=expiring_within_days)
        q = q.where(StockBatch.expiry_date.is_not(None), StockBatch.expiry_date <= cutoff, StockBatch.qty_on_hand > 0)
    result = await db.execute(q)
    return [_batch_dict(b) for b in result.scalars().all()]


@router.get("/batches/expiring-soon")
async def batches_expiring_soon(within_days: int = Query(30, ge=0, le=365), db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) + timedelta(days=within_days)
    q = select(StockBatch).where(
        StockBatch.expiry_date.is_not(None),
        StockBatch.expiry_date <= cutoff,
        StockBatch.qty_on_hand > 0,
    ).order_by(StockBatch.expiry_date.asc()).limit(100)
    result = await db.execute(q)
    return [_batch_dict(b) for b in result.scalars().all()]


@router.post("/batches", status_code=201, dependencies=[Depends(require_permission("inventory.batch.manage"))])
async def create_batch(p: BatchCreate, db: AsyncSession = Depends(get_db)):
    prod = await db.get(Product, p.product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    if not prod.track_batch:
        raise HTTPException(400, f"Product {prod.sku} is not batch-tracked — enable tracking first")
    b = StockBatch(
        product_id=p.product_id,
        warehouse_id=p.warehouse_id,
        batch_code=p.batch_code,
        mfg_date=datetime.fromisoformat(p.mfg_date) if p.mfg_date else None,
        expiry_date=datetime.fromisoformat(p.expiry_date) if p.expiry_date else None,
        qty_received=p.qty_received,
        qty_on_hand=p.qty_received,
        cost_per_unit=p.cost_per_unit,
        notes=p.notes,
    )
    db.add(b)
    await db.flush()
    # Matching inbound stock movement for traceability
    if p.qty_received > 0:
        db.add(StockMovement(
            product_id=p.product_id,
            warehouse_id=p.warehouse_id,
            movement_type=MovementType.RECEIPT,
            quantity=p.qty_received,
            unit_cost=p.cost_per_unit,
            reference=f"Batch {p.batch_code}",
            batch_id=b.id,
        ))
    await db.commit()
    await db.refresh(b)
    return _batch_dict(b)


class BatchAdjust(BaseModel):
    qty_delta: float  # positive=receive, negative=issue/scrap
    reason: str | None = None


@router.post("/batches/{batch_id}/adjust", dependencies=[Depends(require_permission("inventory.batch.manage"))])
async def adjust_batch(batch_id: UUID, p: BatchAdjust, db: AsyncSession = Depends(get_db)):
    b = await db.get(StockBatch, batch_id)
    if not b:
        raise HTTPException(404, "Batch not found")
    new_qty = b.qty_on_hand + p.qty_delta
    if new_qty < 0:
        raise HTTPException(400, f"Adjustment would take batch qty below zero (current {b.qty_on_hand}, delta {p.qty_delta})")
    b.qty_on_hand = round(new_qty, 4)
    if b.warehouse_id:
        db.add(StockMovement(
            product_id=b.product_id,
            warehouse_id=b.warehouse_id,
            movement_type=MovementType.ADJUST if p.qty_delta < 0 else MovementType.RECEIPT,
            quantity=abs(p.qty_delta),
            reference=f"Batch {b.batch_code} adjust",
            notes=p.reason,
            batch_id=b.id,
        ))
    await db.commit()
    return _batch_dict(b)


# ── Serial Numbers ──────────────────────────────────────────────────

class SerialCreate(BaseModel):
    product_id: UUID
    serial_no: str
    batch_id: UUID | None = None
    current_warehouse_id: UUID | None = None
    received_date: str | None = None
    notes: str | None = None


class SerialStatusUpdate(BaseModel):
    status: SerialStatus
    current_warehouse_id: UUID | None = None
    notes: str | None = None


def _serial_dict(s: StockSerial) -> dict:
    return {
        "id": str(s.id),
        "product_id": str(s.product_id),
        "serial_no": s.serial_no,
        "batch_id": str(s.batch_id) if s.batch_id else None,
        "current_warehouse_id": str(s.current_warehouse_id) if s.current_warehouse_id else None,
        "status": s.status.value,
        "received_date": s.received_date.isoformat()[:10] if s.received_date else None,
        "notes": s.notes,
    }


@router.get("/serials")
async def list_serials(
    product_id: UUID | None = None,
    status: str | None = None,
    warehouse_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(StockSerial).order_by(StockSerial.created_at.desc()).limit(500)
    if product_id:
        q = q.where(StockSerial.product_id == product_id)
    if status:
        q = q.where(StockSerial.status == SerialStatus(status))
    if warehouse_id:
        q = q.where(StockSerial.current_warehouse_id == warehouse_id)
    result = await db.execute(q)
    return [_serial_dict(s) for s in result.scalars().all()]


@router.post("/serials", status_code=201, dependencies=[Depends(require_permission("inventory.serial.manage"))])
async def create_serial(p: SerialCreate, db: AsyncSession = Depends(get_db)):
    prod = await db.get(Product, p.product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    if not prod.track_serial:
        raise HTTPException(400, f"Product {prod.sku} is not serial-tracked — enable tracking first")
    existing = await db.execute(
        select(StockSerial).where(StockSerial.product_id == p.product_id, StockSerial.serial_no == p.serial_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Serial {p.serial_no} already registered for this product")
    s = StockSerial(
        product_id=p.product_id,
        serial_no=p.serial_no,
        batch_id=p.batch_id,
        current_warehouse_id=p.current_warehouse_id,
        received_date=datetime.fromisoformat(p.received_date) if p.received_date else datetime.now(timezone.utc),
        notes=p.notes,
    )
    db.add(s)
    await db.flush()
    if p.current_warehouse_id:
        db.add(StockMovement(
            product_id=p.product_id,
            warehouse_id=p.current_warehouse_id,
            movement_type=MovementType.RECEIPT,
            quantity=1.0,
            reference=f"Serial {p.serial_no}",
            batch_id=p.batch_id,
            serial_id=s.id,
        ))
    await db.commit()
    await db.refresh(s)
    return _serial_dict(s)


@router.patch("/serials/{serial_id}", dependencies=[Depends(require_permission("inventory.serial.manage"))])
async def update_serial(serial_id: UUID, p: SerialStatusUpdate, db: AsyncSession = Depends(get_db)):
    s = await db.get(StockSerial, serial_id)
    if not s:
        raise HTTPException(404, "Serial not found")
    prev_status = s.status
    s.status = p.status
    if p.current_warehouse_id is not None:
        s.current_warehouse_id = p.current_warehouse_id
    if p.notes:
        s.notes = p.notes
    # If status transitions out of stock (sold/scrapped/in_transit), log an issue movement
    if prev_status == SerialStatus.IN_STOCK and p.status in (SerialStatus.SOLD, SerialStatus.SCRAPPED, SerialStatus.IN_TRANSIT):
        if s.current_warehouse_id:
            db.add(StockMovement(
                product_id=s.product_id,
                warehouse_id=s.current_warehouse_id,
                movement_type=MovementType.ISSUE,
                quantity=1.0,
                reference=f"Serial {s.serial_no} → {p.status.value}",
                batch_id=s.batch_id,
                serial_id=s.id,
            ))
    await db.commit()
    return _serial_dict(s)


# ── Cost / Profit Centers ────────────────────────────────────────────

class CenterCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


def _center_dict(c) -> dict:
    return {
        "id": str(c.id),
        "code": c.code,
        "name": c.name,
        "description": c.description,
        "is_active": c.is_active,
    }


@router.get("/cost-centers")
async def list_cost_centers(active: bool | None = True, db: AsyncSession = Depends(get_db)):
    q = select(CostCenter).order_by(CostCenter.code)
    if active is not None:
        q = q.where(CostCenter.is_active == active)
    r = await db.execute(q)
    return [_center_dict(c) for c in r.scalars().all()]


@router.post("/cost-centers", status_code=201, dependencies=[Depends(require_permission("finance.account.manage"))])
async def create_cost_center(p: CenterCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(CostCenter).where(CostCenter.code == p.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Cost center code '{p.code}' already exists")
    c = CostCenter(code=p.code, name=p.name, description=p.description)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _center_dict(c)


@router.delete("/cost-centers/{center_id}", status_code=204, dependencies=[Depends(require_permission("finance.account.manage"))])
async def deactivate_cost_center(center_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(CostCenter, center_id)
    if not c:
        raise HTTPException(404, "Cost center not found")
    c.is_active = False
    await db.commit()


@router.get("/profit-centers")
async def list_profit_centers(active: bool | None = True, db: AsyncSession = Depends(get_db)):
    q = select(ProfitCenter).order_by(ProfitCenter.code)
    if active is not None:
        q = q.where(ProfitCenter.is_active == active)
    r = await db.execute(q)
    return [_center_dict(c) for c in r.scalars().all()]


@router.post("/profit-centers", status_code=201, dependencies=[Depends(require_permission("finance.account.manage"))])
async def create_profit_center(p: CenterCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(ProfitCenter).where(ProfitCenter.code == p.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Profit center code '{p.code}' already exists")
    c = ProfitCenter(code=p.code, name=p.name, description=p.description)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _center_dict(c)


@router.delete("/profit-centers/{center_id}", status_code=204, dependencies=[Depends(require_permission("finance.account.manage"))])
async def deactivate_profit_center(center_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(ProfitCenter, center_id)
    if not c:
        raise HTTPException(404, "Profit center not found")
    c.is_active = False
    await db.commit()


@router.get("/reports/center-pnl", dependencies=[Depends(require_permission("finance.reports.view"))])
async def center_pnl_report(by: str = Query("cost", pattern="^(cost|profit)$"), db: AsyncSession = Depends(get_db)):
    """Group revenue / expense totals by cost or profit center across posted journal lines."""
    column = JournalLine.cost_center_id if by == "cost" else JournalLine.profit_center_id
    centers = (await db.execute(
        select(CostCenter if by == "cost" else ProfitCenter).order_by((CostCenter if by == "cost" else ProfitCenter).code)
    )).scalars().all()
    out = []
    # One row per center; "Unassigned" bucket for lines with no center
    centers_index = {c.id: c for c in centers}
    rows: dict[str, dict] = {}
    q = (
        select(
            column,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0.0),
        )
        .select_from(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .join(Account, JournalLine.account_id == Account.id)
        .where(JournalEntry.is_posted == True)  # noqa: E712
        .group_by(column, Account.account_type)
    )
    result = await db.execute(q)
    for center_id, account_type, balance in result.all():
        key = str(center_id) if center_id else "_unassigned"
        if key not in rows:
            c = centers_index.get(center_id) if center_id else None
            rows[key] = {
                "center_id": str(center_id) if center_id else None,
                "code": c.code if c else "—",
                "name": c.name if c else "Unassigned",
                "revenue": 0.0,
                "expense": 0.0,
                "net": 0.0,
            }
        if str(account_type.value) == "revenue" if hasattr(account_type, "value") else str(account_type) == "revenue":
            rows[key]["revenue"] = round(-float(balance), 2)
        elif str(account_type.value) == "expense" if hasattr(account_type, "value") else str(account_type) == "expense":
            rows[key]["expense"] = round(float(balance), 2)
        rows[key]["net"] = round(rows[key]["revenue"] - rows[key]["expense"], 2)
    out = list(rows.values())
    out.sort(key=lambda r: r["code"])
    return out


# ── Stripe Checkout for invoices (#80) ──────────────────────────────

@router.post("/invoices/{invoice_id}/checkout-session", dependencies=[Depends(require_permission("finance.payment.record"))])
async def create_invoice_checkout(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    """Create a Stripe Checkout Session for the outstanding amount on this invoice.
    Returns `{ url, session_id }` — caller opens `url` in a new tab."""
    from app.services.stripe_client import create_checkout_session, is_configured
    from app.config import settings
    if not is_configured():
        raise HTTPException(503, "Stripe not configured — set STRIPE_SECRET_KEY")
    inv = await db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.PAID:
        raise HTTPException(400, "Invoice is already paid")
    outstanding = round((inv.total or 0.0) - (inv.paid_amount or 0.0), 2)
    if outstanding <= 0:
        raise HTTPException(400, "No outstanding balance")
    base = settings.app_base_url.rstrip("/")
    success = f"{base}/finance/invoices?stripe=success&inv={inv.id}"
    cancel = f"{base}/finance/invoices?stripe=cancelled&inv={inv.id}"
    try:
        session = await create_checkout_session(
            invoice_id=str(inv.id),
            invoice_number=inv.invoice_number,
            amount_due=outstanding,
            currency=inv.currency,
            success_url=success,
            cancel_url=cancel,
        )
    except Exception as e:
        raise HTTPException(502, f"Stripe error: {e}")
    inv.stripe_session_id = session.get("id")
    await db.commit()
    return {"url": session.get("url"), "session_id": session.get("id")}
