"""Pricing + returns router (#2, #3)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.erp import Invoice, InvoiceItem, InvoiceStatus
from app.models.pricing import (
    DiscountRule, DiscountType, PriceList, PriceListItem,
    ReturnLine, ReturnMerchandise, ReturnStatus,
)
from app.services.pricing import price_cart
from app.services.workspaces import get_active_workspace_id

router = APIRouter(prefix="/api/pricing", tags=["pricing"], dependencies=[Depends(get_current_user)])
returns_router = APIRouter(prefix="/api/returns", tags=["returns"], dependencies=[Depends(get_current_user)])


# ── Price lists ────────────────────────────────────────────────────

class PriceListIn(BaseModel):
    name: str
    currency: str = "USD"


class PriceListItemIn(BaseModel):
    product_id: UUID
    unit_price: float
    min_quantity: float = 1.0


@router.get("/lists")
async def list_price_lists(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PriceList).order_by(PriceList.name))).scalars().all()
    return [{"id": str(r.id), "name": r.name, "currency": r.currency, "is_active": r.is_active} for r in rows]


@router.post("/lists", status_code=201, dependencies=[Depends(require_permission("finance.pricing.manage"))])
async def create_price_list(p: PriceListIn, request: Request,
                            current_user = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    ws_id = await get_active_workspace_id(request, current_user, db)
    pl = PriceList(name=p.name, currency=p.currency, workspace_id=ws_id)
    db.add(pl); await db.commit(); await db.refresh(pl)
    return {"id": str(pl.id), "name": pl.name}


@router.get("/lists/{list_id}/items")
async def list_price_list_items(list_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(PriceListItem).where(PriceListItem.price_list_id == list_id)
        .order_by(PriceListItem.product_id, PriceListItem.min_quantity)
    )).scalars().all()
    return [{"id": str(r.id), "product_id": str(r.product_id),
             "unit_price": r.unit_price, "min_quantity": r.min_quantity} for r in rows]


@router.post("/lists/{list_id}/items", status_code=201,
             dependencies=[Depends(require_permission("finance.pricing.manage"))])
async def add_price_list_item(list_id: UUID, p: PriceListItemIn, db: AsyncSession = Depends(get_db)):
    pl = await db.get(PriceList, list_id)
    if not pl:
        raise HTTPException(404, "Price list not found")
    existing = (await db.execute(
        select(PriceListItem)
        .where(PriceListItem.price_list_id == list_id)
        .where(PriceListItem.product_id == p.product_id)
        .where(PriceListItem.min_quantity == p.min_quantity)
    )).scalar_one_or_none()
    if existing:
        existing.unit_price = p.unit_price
        await db.commit()
        return {"id": str(existing.id), "updated": True}
    it = PriceListItem(price_list_id=list_id, product_id=p.product_id,
                       unit_price=p.unit_price, min_quantity=p.min_quantity)
    db.add(it); await db.commit(); await db.refresh(it)
    return {"id": str(it.id)}


# ── Discounts / coupons ────────────────────────────────────────────

class DiscountIn(BaseModel):
    name: str
    code: str | None = None
    discount_type: DiscountType = DiscountType.PERCENT
    value: float
    min_subtotal: float = 0.0
    starts_at: str | None = None
    ends_at: str | None = None
    max_redemptions: int | None = None


@router.get("/discounts")
async def list_discounts(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DiscountRule).order_by(DiscountRule.created_at.desc()))).scalars().all()
    return [{
        "id": str(r.id), "name": r.name, "code": r.code,
        "discount_type": r.discount_type.value, "value": r.value,
        "min_subtotal": r.min_subtotal, "is_active": r.is_active,
        "redemptions": r.redemptions, "max_redemptions": r.max_redemptions,
        "starts_at": r.starts_at.isoformat() if r.starts_at else None,
        "ends_at": r.ends_at.isoformat() if r.ends_at else None,
    } for r in rows]


@router.post("/discounts", status_code=201,
             dependencies=[Depends(require_permission("finance.pricing.manage"))])
async def create_discount(p: DiscountIn, request: Request,
                          current_user = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    ws_id = await get_active_workspace_id(request, current_user, db)
    r = DiscountRule(
        workspace_id=ws_id, name=p.name, code=p.code,
        discount_type=p.discount_type, value=p.value, min_subtotal=p.min_subtotal,
        starts_at=datetime.fromisoformat(p.starts_at) if p.starts_at else None,
        ends_at=datetime.fromisoformat(p.ends_at) if p.ends_at else None,
        max_redemptions=p.max_redemptions,
    )
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id), "code": r.code}


# ── Quote the cart (preview) ───────────────────────────────────────

class CartItemIn(BaseModel):
    product_id: UUID
    quantity: float = 1.0


class CartQuoteIn(BaseModel):
    items: list[CartItemIn]
    price_list_id: UUID | None = None
    coupon_code: str | None = None


@router.post("/quote")
async def quote_cart(p: CartQuoteIn, request: Request,
                     current_user = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    ws_id = await get_active_workspace_id(request, current_user, db)
    return await price_cart(
        db,
        [it.model_dump() for it in p.items],
        price_list_id=p.price_list_id,
        coupon_code=p.coupon_code,
        workspace_id=ws_id,
    )


# ── Returns / Refunds (#3) ─────────────────────────────────────────

class ReturnLineIn(BaseModel):
    invoice_item_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0


class ReturnCreateIn(BaseModel):
    invoice_id: UUID
    rma_number: str
    reason: str | None = None
    lines: list[ReturnLineIn] = []


@returns_router.get("")
async def list_returns(invoice_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ReturnMerchandise).order_by(ReturnMerchandise.created_at.desc()).limit(200)
    if invoice_id:
        q = q.where(ReturnMerchandise.invoice_id == invoice_id)
    rows = (await db.execute(q)).scalars().all()
    return [{
        "id": str(r.id), "invoice_id": str(r.invoice_id), "rma_number": r.rma_number,
        "status": r.status.value, "refund_amount": r.refund_amount, "reason": r.reason,
        "received_at": r.received_at.isoformat() if r.received_at else None,
        "refunded_at": r.refunded_at.isoformat() if r.refunded_at else None,
        "created_at": r.created_at.isoformat(),
    } for r in rows]


@returns_router.post("", status_code=201,
                     dependencies=[Depends(require_permission("finance.refund.manage"))])
async def create_return(p: ReturnCreateIn, request: Request,
                        current_user = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    inv = await db.get(Invoice, p.invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    ws_id = await get_active_workspace_id(request, current_user, db)
    refund_amount = sum((ln.unit_price or 0.0) * (ln.quantity or 0.0) for ln in p.lines)
    r = ReturnMerchandise(
        workspace_id=ws_id, invoice_id=p.invoice_id, rma_number=p.rma_number,
        reason=p.reason, refund_amount=round(refund_amount, 2),
        status=ReturnStatus.REQUESTED,
    )
    db.add(r); await db.flush()
    for ln in p.lines:
        amt = round((ln.unit_price or 0.0) * (ln.quantity or 0.0), 2)
        db.add(ReturnLine(return_id=r.id, invoice_item_id=ln.invoice_item_id,
                          description=ln.description, quantity=ln.quantity,
                          unit_price=ln.unit_price, amount=amt))
    await db.commit(); await db.refresh(r)
    return {"id": str(r.id), "rma_number": r.rma_number}


@returns_router.patch("/{return_id}/status",
                      dependencies=[Depends(require_permission("finance.refund.manage"))])
async def update_return_status(return_id: UUID, new_status: ReturnStatus,
                               db: AsyncSession = Depends(get_db)):
    r = await db.get(ReturnMerchandise, return_id)
    if not r:
        raise HTTPException(404, "Return not found")
    now = datetime.utcnow()
    r.status = new_status
    if new_status == ReturnStatus.RECEIVED and not r.received_at:
        r.received_at = now
    if new_status == ReturnStatus.REFUNDED and not r.refunded_at:
        r.refunded_at = now
        # Push the invoice toward a credited state — don't try to draw up a
        # credit-note here; that's a separate workflow. Just flip status.
        inv = await db.get(Invoice, r.invoice_id)
        if inv and inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            # Leave payment accounting to the payment module. We just mark
            # refunded-at so downstream reports can detect it.
            pass
    await db.commit()
    return {"id": str(r.id), "status": r.status.value}
