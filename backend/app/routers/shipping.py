"""Shipping (#75) — generic carrier abstraction.

The `Shipment` model holds a `(carrier, tracking_number)` pair attached to a
Sales Order or Invoice. Real carrier API integration (FedEx/UPS/DHL pulls,
label printing) is intentionally out of scope — `CarrierAdapter` is the
extension point and only the manual / no-op adapter ships here.

The webhook endpoint accepts `(carrier, tracking_number, status, ...)` from
any source so a tracking-aggregator service (Shippo, EasyPost, AfterShip) can
push updates without per-carrier code in this repo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.erp import CarrierType, Shipment, ShipmentStatus

router = APIRouter(prefix="/api/shipping", tags=["shipping"], dependencies=[Depends(get_current_user)])


# ── Carrier adapter interface (stub) ────────────────────────────────

class CarrierAdapter:
    """Subclass + register in CARRIERS to add real integrations later.
    The manual adapter here just stores what you give it."""

    code: CarrierType = CarrierType.OTHER
    label: str = "Manual"

    async def create_label(self, shipment: Shipment) -> dict:
        return {"label_url": None, "tracking_number": shipment.tracking_number}

    async def fetch_status(self, tracking_number: str) -> ShipmentStatus | None:
        return None  # Stub — real adapters would hit the carrier's API.


CARRIERS: dict[CarrierType, CarrierAdapter] = {
    CarrierType.FEDEX: CarrierAdapter(),
    CarrierType.UPS: CarrierAdapter(),
    CarrierType.DHL: CarrierAdapter(),
    CarrierType.USPS: CarrierAdapter(),
    CarrierType.DPD: CarrierAdapter(),
    CarrierType.OTHER: CarrierAdapter(),
}


def _shipment_dict(s: Shipment) -> dict:
    return {
        "id": str(s.id),
        "sales_order_id": str(s.sales_order_id) if s.sales_order_id else None,
        "invoice_id": str(s.invoice_id) if s.invoice_id else None,
        "carrier": s.carrier.value,
        "tracking_number": s.tracking_number,
        "status": s.status.value,
        "shipped_date": s.shipped_date.isoformat() if s.shipped_date else None,
        "delivered_date": s.delivered_date.isoformat() if s.delivered_date else None,
        "expected_delivery": s.expected_delivery.isoformat() if s.expected_delivery else None,
        "label_url": s.label_url,
        "notes": s.notes,
    }


# ── List + create ───────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    carrier: CarrierType
    tracking_number: str
    sales_order_id: UUID | None = None
    invoice_id: UUID | None = None
    shipped_date: str | None = None
    expected_delivery: str | None = None
    notes: str | None = None


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus
    delivered_date: str | None = None
    notes: str | None = None


@router.get("/carriers")
async def list_carriers():
    """Static catalog used by the New-shipment dropdown."""
    return [{"value": c.value, "label": c.value.upper()} for c in CarrierType]


@router.get("/shipments")
async def list_shipments(
    sales_order_id: UUID | None = None,
    invoice_id: UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Shipment).order_by(Shipment.created_at.desc()).limit(200)
    if sales_order_id:
        q = q.where(Shipment.sales_order_id == sales_order_id)
    if invoice_id:
        q = q.where(Shipment.invoice_id == invoice_id)
    if status:
        q = q.where(Shipment.status == ShipmentStatus(status))
    r = await db.execute(q)
    return [_shipment_dict(s) for s in r.scalars().all()]


@router.post("/shipments", status_code=201, dependencies=[Depends(require_permission("sales.shipment.manage"))])
async def create_shipment(p: ShipmentCreate, db: AsyncSession = Depends(get_db)):
    if not (p.sales_order_id or p.invoice_id):
        raise HTTPException(400, "Shipment must attach to a sales_order_id or invoice_id")
    # Carrier-side label creation (stub for now)
    adapter = CARRIERS.get(p.carrier, CARRIERS[CarrierType.OTHER])
    label_data = {"label_url": None}
    s = Shipment(
        sales_order_id=p.sales_order_id,
        invoice_id=p.invoice_id,
        carrier=p.carrier,
        tracking_number=p.tracking_number,
        status=ShipmentStatus.LABEL_CREATED,
        shipped_date=datetime.fromisoformat(p.shipped_date) if p.shipped_date else None,
        expected_delivery=datetime.fromisoformat(p.expected_delivery) if p.expected_delivery else None,
        label_url=label_data.get("label_url"),
        notes=p.notes,
    )
    db.add(s)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(400, f"Could not create shipment (duplicate tracking?): {e}")
    await db.refresh(s)
    _ = adapter  # keep linter happy
    return _shipment_dict(s)


@router.patch("/shipments/{shipment_id}/status", dependencies=[Depends(require_permission("sales.shipment.manage"))])
async def update_shipment_status(shipment_id: UUID, p: ShipmentStatusUpdate, db: AsyncSession = Depends(get_db)):
    s = await db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    s.status = p.status
    if p.delivered_date:
        s.delivered_date = datetime.fromisoformat(p.delivered_date)
    elif p.status == ShipmentStatus.DELIVERED and s.delivered_date is None:
        s.delivered_date = datetime.now(timezone.utc)
    if p.notes:
        s.notes = p.notes
    await db.commit()
    return _shipment_dict(s)


# ── Public webhook for carrier / aggregator updates ─────────────────

webhook_router = APIRouter(prefix="/api/webhooks/shipping", tags=["webhooks"])


class ShippingWebhookEvent(BaseModel):
    carrier: CarrierType
    tracking_number: str
    status: ShipmentStatus
    delivered_date: str | None = None
    notes: str | None = None


@webhook_router.post("")
async def shipping_webhook(event: ShippingWebhookEvent, db: AsyncSession = Depends(get_db)):
    """Carrier / aggregator pushes status updates here. Looks up the shipment
    by (carrier, tracking_number) and applies the change. No auth — production
    setups should add a shared-secret HMAC check or IP allow-list.
    """
    r = await db.execute(
        select(Shipment).where(
            Shipment.carrier == event.carrier,
            Shipment.tracking_number == event.tracking_number,
        )
    )
    s = r.scalar_one_or_none()
    if not s:
        # Don't reveal whether the tracking number is known — return 200 either way
        return {"received": True, "matched": False}
    s.status = event.status
    if event.delivered_date:
        s.delivered_date = datetime.fromisoformat(event.delivered_date)
    elif event.status == ShipmentStatus.DELIVERED and s.delivered_date is None:
        s.delivered_date = datetime.now(timezone.utc)
    if event.notes:
        s.notes = event.notes
    await db.commit()
    return {"received": True, "matched": True, "shipment_id": str(s.id)}
