"""FIFO stock consumption + barcode lookup (#5).

`issue_fifo(db, product_id, warehouse_id, quantity, ...)` drains the
oldest batches first — the standard First-In-First-Out accounting
convention. Returns a list of per-batch consumption rows and records
an `ISSUE` StockMovement for each. Raises HTTP 400 when there isn't
enough on hand.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.erp import MovementType, Product, StockBatch, StockMovement


async def issue_fifo(
    db: AsyncSession,
    product_id,
    warehouse_id,
    quantity: float,
    reference: str | None = None,
    bin_id=None,
    notes: str | None = None,
) -> list[dict[str, Any]]:
    """Consume `quantity` units of `product_id` at `warehouse_id` by
    draining batches in order of oldest `mfg_date` (nulls last), then
    earliest `created_at`. Writes an ISSUE StockMovement per batch.
    Returns a list of {batch_id, qty_taken, unit_cost}."""
    if quantity <= 0:
        raise HTTPException(400, "quantity must be positive")
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    batches = (await db.execute(
        select(StockBatch)
        .where(StockBatch.product_id == product_id)
        .where(StockBatch.qty_on_hand > 0)
        .where((StockBatch.warehouse_id == warehouse_id) | (StockBatch.warehouse_id.is_(None)))
        .order_by(StockBatch.mfg_date.asc().nullslast(), StockBatch.created_at.asc())
    )).scalars().all()

    available = sum(b.qty_on_hand for b in batches)
    if available + 1e-9 < quantity:
        raise HTTPException(400, f"Insufficient stock: have {available}, need {quantity}")

    remaining = float(quantity)
    consumed: list[dict[str, Any]] = []
    for b in batches:
        if remaining <= 1e-9:
            break
        take = min(b.qty_on_hand, remaining)
        b.qty_on_hand = round(b.qty_on_hand - take, 4)
        remaining = round(remaining - take, 4)
        db.add(StockMovement(
            product_id=product_id, warehouse_id=warehouse_id, bin_id=bin_id,
            movement_type=MovementType.ISSUE,
            quantity=-take, unit_cost=b.cost_per_unit,
            batch_id=b.id, reference=reference, notes=notes,
            movement_date=datetime.utcnow(),
        ))
        consumed.append({
            "batch_id": str(b.id), "batch_code": b.batch_code,
            "qty_taken": take, "unit_cost": b.cost_per_unit,
            "remaining_in_batch": b.qty_on_hand,
        })
    await db.commit()
    return consumed


async def scan_barcode(db: AsyncSession, code: str):
    """Resolve a scanned barcode to a product row. Used by the mobile
    picker screen. Returns None if unknown."""
    if not code:
        return None
    row = (await db.execute(
        select(Product).where(Product.barcode == code)
    )).scalar_one_or_none()
    return row
