"""Pricing calculation (#2).

`resolve_unit_price(product, price_list, qty)` picks the right unit price
given a product, an optional price-list override, and quantity (for tiered
pricing).

`apply_discount(subtotal, rule)` computes the discount amount for a given
rule against a subtotal, honouring percent vs amount + minimum subtotal.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import DiscountRule, DiscountType, PriceListItem


async def resolve_unit_price(db: AsyncSession, product, price_list_id, quantity: float) -> float:
    """Given a product, optional price_list_id, and quantity, return the
    applicable unit price. Falls back to the product's base unit_price."""
    if price_list_id is None:
        return product.unit_price or 0.0
    # Highest min_quantity that is <= qty wins (tier pricing).
    row = (await db.execute(
        select(PriceListItem)
        .where(PriceListItem.price_list_id == price_list_id)
        .where(PriceListItem.product_id == product.id)
        .where(PriceListItem.min_quantity <= quantity)
        .order_by(PriceListItem.min_quantity.desc())
        .limit(1)
    )).scalar_one_or_none()
    if row is not None:
        return row.unit_price
    return product.unit_price or 0.0


async def lookup_discount(db: AsyncSession, code: str | None, workspace_id=None) -> DiscountRule | None:
    """Find an active discount either by code, or (if code is None) the
    first auto-apply rule. Honours is_active + start/end window +
    redemption caps."""
    now = datetime.utcnow()
    q = select(DiscountRule).where(DiscountRule.is_active.is_(True))
    if workspace_id is not None:
        q = q.where((DiscountRule.workspace_id == workspace_id) | (DiscountRule.workspace_id.is_(None)))
    if code:
        q = q.where(DiscountRule.code == code)
    else:
        q = q.where(DiscountRule.code.is_(None))
    rows = (await db.execute(q)).scalars().all()
    for r in rows:
        if r.starts_at and r.starts_at > now:
            continue
        if r.ends_at and r.ends_at < now:
            continue
        if r.max_redemptions is not None and r.redemptions >= r.max_redemptions:
            continue
        return r
    return None


def apply_discount(subtotal: float, rule: DiscountRule | None) -> float:
    """Amount to subtract from the subtotal. 0 if no rule applies or the
    subtotal doesn't meet the rule's minimum."""
    if rule is None or subtotal < (rule.min_subtotal or 0.0):
        return 0.0
    if rule.discount_type == DiscountType.PERCENT:
        # Clamp percent to [0, 100] so nobody accidentally writes 1000.
        pct = max(0.0, min(100.0, rule.value or 0.0))
        return round(subtotal * pct / 100.0, 2)
    # AMOUNT — cap at the subtotal so we don't go negative.
    return round(min(rule.value or 0.0, subtotal), 2)


async def price_cart(db: AsyncSession, items: list[dict], price_list_id=None,
                     coupon_code: str | None = None, workspace_id=None) -> dict:
    """Calculate line pricing, subtotal, discount, total for a cart.
    `items` is a list of {product_id, quantity}."""
    from app.models.erp import Product
    lines = []
    subtotal = 0.0
    for it in items:
        prod = await db.get(Product, it["product_id"])
        if not prod:
            continue
        qty = float(it.get("quantity") or 1)
        unit_price = await resolve_unit_price(db, prod, price_list_id, qty)
        amount = round(unit_price * qty, 2)
        subtotal += amount
        lines.append({
            "product_id": str(prod.id), "sku": prod.sku, "name": prod.name,
            "quantity": qty, "unit_price": unit_price, "amount": amount,
        })
    rule = await lookup_discount(db, coupon_code, workspace_id=workspace_id)
    discount = apply_discount(subtotal, rule)
    return {
        "lines": lines,
        "subtotal": round(subtotal, 2),
        "discount": discount,
        "discount_label": (rule.name if rule else None),
        "total": round(max(0.0, subtotal - discount), 2),
    }
