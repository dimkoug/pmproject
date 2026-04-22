"""Webhook signing + retries (Phase 4 #8).

Covers:
  * _sign() produces a deterministic HMAC matching the canonical format
  * _next_attempt_time() returns None after MAX_ATTEMPTS
  * queue_delivery() records delivery row + schedules retry on failure
  * retry_pending_deliveries() picks up due deliveries and advances attempts
  * /api/webhooks/deliveries/{id}/retry force-requeues
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _patch_webhook_session(monkeypatch):
    """The webhook service opens its own DB sessions via
    `app.database.async_session`, which points at the production engine.
    Redirect to the test sqlite session factory so the service and tests
    see the same rows."""
    from tests.conftest import async_session_test
    import app.services.webhooks as mod
    monkeypatch.setattr(mod, "async_session", async_session_test)


class TestHmacSigning:
    def test_sign_deterministic(self):
        from app.services.webhooks import _sign
        a = _sign("secret", 1234567890, '{"hello":"world"}')
        b = _sign("secret", 1234567890, '{"hello":"world"}')
        assert a == b
        assert a.startswith("sha256=")

    def test_sign_changes_with_body(self):
        from app.services.webhooks import _sign
        a = _sign("secret", 1234567890, '{"a":1}')
        b = _sign("secret", 1234567890, '{"a":2}')
        assert a != b

    def test_sign_changes_with_secret(self):
        from app.services.webhooks import _sign
        a = _sign("secret1", 1, '{}')
        b = _sign("secret2", 1, '{}')
        assert a != b

    def test_sign_matches_hmac_spec(self):
        """Format: sha256=HMAC_SHA256(secret, "<ts>.<body>")"""
        import hmac, hashlib
        from app.services.webhooks import _sign
        expected = "sha256=" + hmac.new(
            b"s", b"42.body", hashlib.sha256,
        ).hexdigest()
        assert _sign("s", 42, "body") == expected


class TestBackoffSchedule:
    def test_exhausted_returns_none(self):
        from app.services.webhooks import _next_attempt_time, MAX_ATTEMPTS
        assert _next_attempt_time(MAX_ATTEMPTS) is None
        assert _next_attempt_time(MAX_ATTEMPTS + 10) is None

    def test_early_attempts_have_increasing_delays(self):
        """The backoff schedule is [30, 120, 600, 1800, 7200] seconds,
        indexed by the attempt count just completed. Each successive wait
        is strictly longer than the previous one."""
        from app.services.webhooks import _next_attempt_time
        base = datetime.now(timezone.utc)
        waits = [(_next_attempt_time(n) - base).total_seconds() for n in (0, 1, 2, 3, 4)]
        # Strictly increasing
        assert all(b > a for a, b in zip(waits, waits[1:]))
        # First wait is ≥ 30s, last is ≥ 2 hours
        assert waits[0] >= 29
        assert waits[-1] >= 7000


class TestQueueDelivery:
    async def test_inactive_hook_returns_none(self):
        from tests.conftest import async_session_test
        from app.models.cross import Webhook
        from app.services.webhooks import queue_delivery
        async with async_session_test() as db:
            w = Webhook(name="off", url="http://127.0.0.1:9999/x", secret="s", is_active=False)
            db.add(w); await db.commit(); await db.refresh(w)
            wid = str(w.id)
        result = await queue_delivery(wid, "test.event", "{}")
        assert result is None

    async def test_failed_delivery_schedules_retry(self):
        """Point at an unroutable address so httpx errors, attempts → 1,
        next_attempt_at gets set in the future."""
        from tests.conftest import async_session_test
        from app.models.cross import Webhook, WebhookDelivery
        from app.services.webhooks import queue_delivery
        from sqlalchemy import select
        async with async_session_test() as db:
            w = Webhook(name="broken", url="http://127.0.0.1:1/never", secret="s", is_active=True)
            db.add(w); await db.commit(); await db.refresh(w)
            wid = str(w.id)

        did = await queue_delivery(wid, "test.fail", '{"k":"v"}')
        assert did is not None

        async with async_session_test() as db:
            rows = (await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.event == "test.fail")
            )).scalars().all()
        assert len(rows) == 1
        d = rows[0]
        assert d.attempts == 1
        assert d.delivered_at is None
        assert d.next_attempt_at is not None  # scheduled for retry
        # SQLite drops tzinfo on round-trip; compare against naive UTC-now.
        now_ref = datetime.now(timezone.utc)
        if d.next_attempt_at.tzinfo is None:
            now_ref = now_ref.replace(tzinfo=None)
        assert d.next_attempt_at > now_ref


class TestRetrySweeper:
    async def test_sweeper_skips_future_deliveries(self):
        from tests.conftest import async_session_test
        from app.models.cross import Webhook, WebhookDelivery
        from app.services.webhooks import retry_pending_deliveries
        async with async_session_test() as db:
            w = Webhook(name="later", url="http://x/y", secret="s", is_active=True)
            db.add(w); await db.commit(); await db.refresh(w)
            db.add(WebhookDelivery(
                webhook_id=w.id, event="e", payload="{}",
                attempts=1, next_attempt_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ))
            await db.commit()

        result = await retry_pending_deliveries(batch_size=50)
        assert result["examined"] == 0  # nothing due yet

    async def test_sweeper_advances_attempts_and_sets_next(self):
        from tests.conftest import async_session_test
        from app.models.cross import Webhook, WebhookDelivery
        from app.services.webhooks import retry_pending_deliveries
        from sqlalchemy import select
        async with async_session_test() as db:
            w = Webhook(name="due", url="http://127.0.0.1:1/x", secret="s", is_active=True)
            db.add(w); await db.commit(); await db.refresh(w)
            past = datetime.now(timezone.utc) - timedelta(minutes=5)
            db.add(WebhookDelivery(
                webhook_id=w.id, event="e.due", payload="{}",
                attempts=1, next_attempt_at=past,
            ))
            await db.commit()

        result = await retry_pending_deliveries(batch_size=50)
        assert result["examined"] == 1
        # delivery failed again (unroutable URL) → retry or exhausted
        assert result["retry"] + result["exhausted"] == 1

        async with async_session_test() as db:
            d = (await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.event == "e.due")
            )).scalar_one()
        assert d.attempts == 2

    async def test_sweeper_exhausts_after_max_attempts(self):
        from tests.conftest import async_session_test
        from app.models.cross import Webhook, WebhookDelivery
        from app.services.webhooks import retry_pending_deliveries, MAX_ATTEMPTS
        from sqlalchemy import select
        async with async_session_test() as db:
            w = Webhook(name="max", url="http://127.0.0.1:1/x", secret="s", is_active=True)
            db.add(w); await db.commit(); await db.refresh(w)
            db.add(WebhookDelivery(
                webhook_id=w.id, event="e.max", payload="{}",
                attempts=MAX_ATTEMPTS, next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ))
            await db.commit()

        result = await retry_pending_deliveries(batch_size=50)
        assert result["exhausted"] >= 1

        async with async_session_test() as db:
            d = (await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.event == "e.max")
            )).scalar_one()
        assert d.next_attempt_at is None
        assert d.attempts == MAX_ATTEMPTS + 1


class TestForceRetryEndpoint:
    async def test_retry_endpoint_requeues_delivery(self, client: AsyncClient):
        from tests.conftest import async_session_test
        from app.models.cross import Webhook, WebhookDelivery
        from sqlalchemy import select
        async with async_session_test() as db:
            w = Webhook(name="manual", url="http://x", secret="s", is_active=True)
            db.add(w); await db.commit(); await db.refresh(w)
            d = WebhookDelivery(
                webhook_id=w.id, event="e", payload="{}",
                attempts=2, next_attempt_at=None,
            )
            db.add(d); await db.commit(); await db.refresh(d)
            did = str(d.id)

        r = await client.post(f"/api/webhooks/deliveries/{did}/retry")
        assert r.status_code == 200
        assert r.json()["requeued"] is True

        async with async_session_test() as db:
            from uuid import UUID
            row = await db.get(WebhookDelivery, UUID(did))
        assert row.next_attempt_at is not None

    async def test_retry_unknown_id_404(self, client: AsyncClient):
        r = await client.post(
            "/api/webhooks/deliveries/00000000-0000-4000-8000-000000000000/retry"
        )
        assert r.status_code == 404
