"""SMS delivery — Twilio adapter, with the same shape as `email.py`.

Two layers:
  * `send_sms_now()` — blocking REST call to Twilio (test/debug only).
  * `send_sms_task` — Celery task on the reports queue; what request handlers
    should call so they don't block on the network.

Behaviour when SMS isn't configured:
  * `SMS_ENABLED` env flag is the master switch — when off, every call logs the
    would-have-been message and returns quietly. This lets you develop locally
    and in CI without real Twilio credentials.

The Twilio call is made via `urllib.request` so we don't add a hard dependency
on the `twilio` Python SDK — keeps the image lean.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.celery_app import celery
from app.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(
        settings.sms_enabled
        and settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from
    )


def send_sms_now(to: str, body: str) -> None:
    if not _is_configured():
        logger.info("SMS not configured — would have sent to %s: %s", to, body[:80])
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    data = urllib.parse.urlencode({
        "From": settings.twilio_from,
        "To": to,
        "Body": body,
    }).encode("utf-8")
    creds = base64.b64encode(
        f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode("utf-8")
    ).decode("ascii")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            logger.info("Sent SMS to %s sid=%s", to, payload.get("sid"))
    except urllib.error.HTTPError as e:
        body_resp = e.read().decode("utf-8", errors="replace")
        logger.warning("Twilio rejected SMS to %s [%s]: %s", to, e.code, body_resp[:200])
    except Exception:
        logger.exception("SMS send failed to %s", to)


@celery.task(name="send_sms_task", bind=True, max_retries=3)
def send_sms_task(self, to: str, body: str) -> None:
    try:
        send_sms_now(to, body)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)


def queue_sms(to: str | None, body: str) -> None:
    """Best-effort enqueue. Silently no-ops if `to` is missing or SMS is off."""
    if not to:
        return
    if not settings.sms_enabled:
        logger.debug("SMS disabled — skipping send to %s", to)
        return
    try:
        send_sms_task.delay(to, body)
    except Exception:
        logger.warning("Failed to queue SMS to %s", to, exc_info=True)
