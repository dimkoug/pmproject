"""Webhook delivery with HMAC-SHA256 signing + exponential retry (#8).

Two entry points:
  * `queue_delivery(hook_id, event, payload_json)` — records a `WebhookDelivery`
    row and attempts immediate delivery. If it fails, schedules the next
    attempt and returns — the sweeper (driven by beat) picks it up later.
  * `retry_pending_deliveries()` — called by the celery beat task
    `retry_webhook_deliveries_task`. Picks up any delivery whose
    `next_attempt_at` is due and retries once.

Signing format (compatible with GitHub/Stripe style):
  * `X-Webhook-Timestamp`: unix seconds
  * `X-Webhook-Signature`: `sha256=<hex>` where hex = HMAC-SHA256(secret, "<ts>.<body>")
  * `X-Webhook-Event`: event name
  * `X-Webhook-Delivery`: delivery UUID (for idempotency)

Retry schedule: 30s, 2m, 10m, 30m, 2h (5 attempts total). After that the
delivery is marked permanently failed (next_attempt_at set to NULL).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.database import async_session
from app.models.cross import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

# Backoff in seconds per attempt (attempt count is 1-indexed by the time we look it up)
_BACKOFF_SCHEDULE = [30, 120, 600, 1800, 7200]
MAX_ATTEMPTS = len(_BACKOFF_SCHEDULE)


def _sign(secret: str, ts: int, body: str) -> str:
    mac = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


async def _attempt_post(w: Webhook, delivery_id: UUID, event: str, body: str) -> tuple[int | None, str | None]:
    try:
        import httpx
    except Exception:
        return None, "httpx not installed"
    ts = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event,
        "X-Webhook-Timestamp": str(ts),
        "X-Webhook-Delivery": str(delivery_id),
        "X-Webhook-Signature": _sign(w.secret or "", ts, body),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(w.url, content=body, headers=headers)
            return r.status_code, None
    except Exception as e:
        return None, str(e)[:1000]


def _next_attempt_time(attempts: int) -> datetime | None:
    """Given we *just* finished attempt N (1-indexed), when's N+1?
    Returns None if we've exhausted retries."""
    if attempts >= MAX_ATTEMPTS:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=_BACKOFF_SCHEDULE[attempts])


async def queue_delivery(hook_id: str, event: str, payload_json: str) -> str | None:
    """Record a delivery row, attempt the POST once, schedule retry if it
    failed. Returns the delivery id (or None if the webhook was inactive)."""
    async with async_session() as db:
        w = await db.get(Webhook, UUID(hook_id))
        if not w or not w.is_active:
            return None
        delivery = WebhookDelivery(
            webhook_id=w.id, event=event, payload=payload_json,
            attempts=0, next_attempt_at=None,
        )
        db.add(delivery)
        await db.flush()  # populate delivery.id without committing yet

        status, err = await _attempt_post(w, delivery.id, event, payload_json)
        delivery.attempts = 1
        delivery.status_code = status
        delivery.error = err
        if status is not None and 200 <= status < 300:
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.next_attempt_at = None
        else:
            delivery.next_attempt_at = _next_attempt_time(1)
        await db.commit()
        return str(delivery.id)


async def retry_pending_deliveries(batch_size: int = 50) -> dict:
    """Sweep for deliveries whose retry time has come due, attempt each once.
    Uses a naive-UTC `now` for the WHERE clause because SQLite-backed tests
    store naive datetimes; Postgres silently coerces either into TIMESTAMPTZ."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sent = 0
    failed = 0
    exhausted = 0
    async with async_session() as db:
        q = (
            select(WebhookDelivery)
            .where(WebhookDelivery.next_attempt_at.is_not(None))
            .where(WebhookDelivery.next_attempt_at <= now)
            .order_by(WebhookDelivery.next_attempt_at.asc())
            .limit(batch_size)
        )
        rows = (await db.execute(q)).scalars().all()
        for d in rows:
            w = await db.get(Webhook, d.webhook_id)
            if not w or not w.is_active:
                d.next_attempt_at = None
                d.error = "webhook disabled"
                exhausted += 1
                continue
            status, err = await _attempt_post(w, d.id, d.event, d.payload)
            d.attempts += 1
            d.status_code = status
            d.error = err
            if status is not None and 200 <= status < 300:
                d.delivered_at = datetime.now(timezone.utc)
                d.next_attempt_at = None
                sent += 1
            else:
                nxt = _next_attempt_time(d.attempts)
                d.next_attempt_at = nxt
                if nxt is None:
                    exhausted += 1
                else:
                    failed += 1
        await db.commit()
    if rows:
        logger.info("webhook retry sweep: sent=%s retry=%s exhausted=%s", sent, failed, exhausted)
    return {"sent": sent, "retry": failed, "exhausted": exhausted, "examined": len(rows)}
