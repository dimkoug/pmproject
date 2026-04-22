"""Stripe client (#80).

Uses `httpx` against Stripe's REST API directly so we don't add the heavyweight
`stripe` SDK as a hard dependency. Two operations:

  * `create_checkout_session(invoice, success_url, cancel_url)` — minimal
    one-line-item Checkout Session for an invoice.
  * `verify_webhook_signature(payload, header)` — HMAC-SHA256 sig check using
    the webhook secret.

When `STRIPE_SECRET_KEY` is unset, callers should branch on `is_configured()`
and surface a friendly "not configured" message instead of calling these.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


async def create_checkout_session(
    invoice_id: str,
    invoice_number: str,
    amount_due: float,
    currency: str | None,
    success_url: str,
    cancel_url: str,
    customer_email: str | None = None,
) -> dict:
    """Create a one-line Checkout Session.

    Stripe expects amounts in the smallest currency unit (cents for USD).
    Returns the parsed JSON response — caller picks `id`, `url`, etc.
    """
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe not configured — set STRIPE_SECRET_KEY")
    cur = (currency or settings.stripe_currency_default).lower()
    amount_minor = int(round(amount_due * 100))
    if amount_minor <= 0:
        raise ValueError("Cannot create checkout session for a zero-amount invoice")

    form = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price_data][currency]": cur,
        "line_items[0][price_data][product_data][name]": f"Invoice {invoice_number}",
        "line_items[0][price_data][unit_amount]": str(amount_minor),
        "line_items[0][quantity]": "1",
        "metadata[invoice_id]": invoice_id,
        "metadata[invoice_number]": invoice_number,
        "client_reference_id": invoice_id,
    }
    if customer_email:
        form["customer_email"] = customer_email

    body = urllib.parse.urlencode(form)
    creds = base64.b64encode(f"{settings.stripe_secret_key}:".encode()).decode()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            content=body,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if r.status_code >= 400:
            logger.warning("Stripe checkout failed [%s]: %s", r.status_code, r.text[:300])
        r.raise_for_status()
        return r.json()


def verify_webhook_signature(payload: bytes, signature_header: str | None) -> dict | None:
    """Validate Stripe's `Stripe-Signature` header. Returns parsed timestamp+sig
    on success, None on failure. The header looks like:

        t=1614637200,v1=abc123...

    Tolerance: 5 minutes (rejects replays older than that).
    """
    if not signature_header or not settings.stripe_webhook_secret:
        return None
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        ts = int(parts.get("t", "0"))
        sig = parts.get("v1", "")
    except Exception:
        return None
    if abs(int(time.time()) - ts) > 300:
        return None  # too old
    signed_payload = f"{ts}.".encode() + payload
    expected = hmac.new(
        settings.stripe_webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return {"timestamp": ts}
