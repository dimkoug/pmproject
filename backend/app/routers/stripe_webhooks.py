"""Stripe webhook handler (#80) — separate router because it must be public
and consume the raw request body for HMAC signature verification."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.erp import Invoice, InvoiceStatus, Payment
from app.services.stripe_client import verify_webhook_signature

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    verified = verify_webhook_signature(payload, sig_header)
    if not verified:
        # Always 401 on bad signature so Stripe retries (and we don't leak info)
        raise HTTPException(status_code=401, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, obj)
    elif event_type == "checkout.session.expired":
        await _handle_checkout_expired(db, obj)
    else:
        logger.info("Stripe webhook: ignoring event type=%s", event_type)

    return {"received": True}


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    invoice_id = (session.get("metadata") or {}).get("invoice_id") or session.get("client_reference_id")
    if not invoice_id:
        logger.warning("Stripe checkout.session.completed: no invoice_id in metadata")
        return
    try:
        inv_uuid = UUID(invoice_id)
    except Exception:
        logger.warning("Stripe checkout.session.completed: invalid invoice_id=%r", invoice_id)
        return

    inv = await db.get(Invoice, inv_uuid)
    if not inv:
        logger.warning("Stripe checkout.session.completed: invoice %s not found", invoice_id)
        return
    # Idempotency — if we already saw this session, no-op
    if inv.stripe_session_id and inv.stripe_session_id != session.get("id"):
        logger.info("Stripe: invoice %s already linked to a different session, skipping", invoice_id)
        return

    amount_paid = float(session.get("amount_total") or 0) / 100.0
    payment_intent_id = session.get("payment_intent")

    db.add(Payment(
        invoice_id=inv.id,
        amount=amount_paid,
        method="stripe",
        reference=session.get("id"),
        notes=f"Stripe payment_intent {payment_intent_id}" if payment_intent_id else None,
    ))
    inv.paid_amount = round((inv.paid_amount or 0.0) + amount_paid, 2)
    inv.stripe_payment_intent_id = payment_intent_id
    if inv.paid_amount + 0.01 >= inv.total:
        inv.status = InvoiceStatus.PAID
    await db.commit()
    logger.info("Stripe: marked invoice %s paid (+ $%.2f)", invoice_id, amount_paid)


async def _handle_checkout_expired(db: AsyncSession, session: dict) -> None:
    invoice_id = (session.get("metadata") or {}).get("invoice_id") or session.get("client_reference_id")
    if not invoice_id:
        return
    try:
        inv_uuid = UUID(invoice_id)
    except Exception:
        return
    inv = await db.get(Invoice, inv_uuid)
    if inv and inv.stripe_session_id == session.get("id"):
        # Clear the abandoned session so the user can retry
        inv.stripe_session_id = None
        await db.commit()
