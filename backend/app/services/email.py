"""Transactional email delivery.

Two layers:
  * `send_email_now()` — blocking SMTP send, intended only for testing/debug.
  * `send_email_task` — Celery task (reports queue) that the app calls instead,
    so request handlers don't block on SMTP.

When `SMTP_HOST` is unset the email layer logs the would-have-been message and
returns quietly — lets you develop locally without real email delivery.

Templates (#6) — `render_template(key, defaults, ctx)` consults the
`email_templates` table for overrides before falling back to code defaults.
Tracking (#7) — when a `template_key` is supplied, outgoing HTML is rewritten
to route clicks through `/api/t/click/{id}` and an open-tracking pixel is appended.
"""

from __future__ import annotations

import logging
import re
import smtplib
import uuid
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import quote

from app.celery_app import celery
from app.config import settings

logger = logging.getLogger(__name__)


# ── Templates (#6) ──────────────────────────────────────────────────

def render_template(key: str, default_subject: str, default_text: str,
                    default_html: str | None, ctx: dict) -> tuple[str, str, str | None]:
    """Resolve a transactional template, preferring the DB override if present.
    Falls back to the provided defaults. Placeholders: `{name}`. Missing keys
    render as empty strings (safer than a KeyError in production).

    Returns (subject, body_text, body_html)."""
    subject, text, html = default_subject, default_text, default_html
    try:
        from sqlalchemy import create_engine, text as _t
        # Sync lookup — this runs inside the celery worker task. We create a
        # short-lived engine so we don't reach into the async app engine from
        # a sync context.
        sync_url = settings.database_url.replace("+asyncpg", "")
        engine = create_engine(sync_url, pool_pre_ping=True, pool_recycle=300)
        with engine.connect() as conn:
            row = conn.execute(
                _t("SELECT subject, body_text, body_html FROM email_templates WHERE key = :k LIMIT 1"),
                {"k": key},
            ).first()
        if row:
            subject = row[0] or subject
            text = row[1] or text
            html = row[2] or html
    except Exception:
        # DB not reachable? Fall through to defaults rather than failing the send.
        logger.debug("email template lookup failed for %s", key, exc_info=True)

    def _sub(s: str) -> str:
        class _D(dict):
            def __missing__(self, k): return ""
        try:
            return s.format_map(_D(ctx))
        except Exception:
            return s
    return _sub(subject), _sub(text), _sub(html) if html else None


# ── Tracking (#7) — open pixel + click-through wrapping ─────────────

_LINK_RE = re.compile(r'href="(https?://[^"#]+)"', re.IGNORECASE)


def _track_html(html: str, recipient: str, template_key: str | None) -> str:
    """Rewrite <a href="..."> links to route through the click-tracking
    endpoint, and append a 1×1 open-pixel at the end."""
    if not html:
        return html
    base = settings.app_base_url.rstrip("/")
    evt = uuid.uuid4().hex
    # Pass the recipient + template key so the tracking endpoint can attribute
    # the event without a dedicated per-send record.
    meta = f"r={quote(recipient)}&k={quote(template_key or '')}"

    def _rewrite(match: re.Match) -> str:
        target = match.group(1)
        return f'href="{base}/api/t/click/{evt}?{meta}&u={quote(target, safe="")}"'

    rewritten = _LINK_RE.sub(_rewrite, html)
    pixel = (
        f'<img src="{base}/api/t/open/{evt}.gif?{meta}" '
        f'alt="" width="1" height="1" style="display:none" />'
    )
    return rewritten + pixel


def send_email_now(to: str, subject: str, body_text: str, body_html: str | None = None,
                   template_key: str | None = None) -> None:
    if body_html and template_key:
        body_html = _track_html(body_html, to, template_key)

    if not settings.smtp_host:
        logger.info("SMTP not configured — would have sent to %s: %s", to, subject)
        return

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Sent email to %s: %s", to, subject)
    except Exception:
        logger.exception("Email send failed to %s", to)


@celery.task(name="send_email_task", bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, body_text: str,
                    body_html: str | None = None, template_key: str | None = None):
    try:
        send_email_now(to, subject, body_text, body_html, template_key=template_key)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ── Convenience wrappers used throughout the app ────────────────────

def _dispatch(key: str, to: str, default_subject: str, default_text: str, default_html: str | None, ctx: dict):
    subject, text, html = render_template(key, default_subject, default_text, default_html, ctx)
    send_email_task.delay(to=to, subject=subject, body_text=text, body_html=html, template_key=key)


def queue_password_reset(to: str, reset_token: str, user_name: str | None = None):
    link = f"{settings.app_base_url}/reset-password?token={reset_token}"
    ctx = {"name": user_name or "", "link": link}
    _dispatch(
        "password_reset", to,
        default_subject="Reset your password",
        default_text="Hi {name},\n\nUse this link to reset your password:\n{link}\n\nIt expires in 1 hour.",
        default_html=(
            "<p>Hi {name},</p>"
            "<p>Use this link to reset your password:</p>"
            "<p><a href=\"{link}\">{link}</a></p>"
            "<p>It expires in 1 hour.</p>"
        ),
        ctx=ctx,
    )


def queue_signature_request(to: str, document_title: str, token: str, message: str | None = None):
    link = f"{settings.app_base_url}/sign/{token}"
    ctx = {"document_title": document_title, "message": message or "", "link": link}
    _dispatch(
        "signature_request", to,
        default_subject="Signature requested: {document_title}",
        default_text="You have been asked to sign the document '{document_title}'.\n\n{message}\n\nOpen it here:\n{link}",
        default_html=(
            "<p>You have been asked to sign the document <strong>{document_title}</strong>.</p>"
            "<p>{message}</p>"
            "<p><a href=\"{link}\">Open document to sign</a></p>"
        ),
        ctx=ctx,
    )


def queue_approval_assigned(to: str, target_type: str, note: str | None = None):
    ctx = {"target_type": target_type, "note": note or "—", "admin_url": f"{settings.app_base_url}/admin"}
    _dispatch(
        "approval_assigned", to,
        default_subject="Approval required: {target_type}",
        default_text="An approval request is waiting for you.\n\nType: {target_type}\nNote: {note}\n\n{admin_url}",
        default_html=(
            "<p>An approval request is waiting for you.</p>"
            "<p><strong>Type:</strong> {target_type}<br><strong>Note:</strong> {note}</p>"
            "<p><a href=\"{admin_url}\">Open approvals inbox</a></p>"
        ),
        ctx=ctx,
    )


def queue_expiry_reminder(to: str, doc_title: str, days_left: int, expiry_date: str):
    ctx = {
        "doc_title": doc_title, "days_left": days_left, "expiry_date": expiry_date,
        "plural": "s" if days_left != 1 else "",
        "docs_url": f"{settings.app_base_url}/documents",
    }
    _dispatch(
        "document_expiry_reminder", to,
        default_subject="Document expiring: {doc_title}",
        default_text="'{doc_title}' expires in {days_left} day{plural} ({expiry_date}).\n\n{docs_url}",
        default_html=(
            "<p><strong>{doc_title}</strong> expires in {days_left} day{plural} ({expiry_date}).</p>"
            "<p><a href=\"{docs_url}\">View document</a></p>"
        ),
        ctx=ctx,
    )


def queue_mention_notification(to: str, actor_name: str, context: str, link: str):
    ctx = {"actor_name": actor_name, "context": context, "link": f"{settings.app_base_url}{link}"}
    _dispatch(
        "mention", to,
        default_subject="{actor_name} mentioned you",
        default_text="{actor_name} mentioned you in {context}.\n\nOpen: {link}",
        default_html=(
            "<p>{actor_name} mentioned you in {context}.</p>"
            "<p><a href=\"{link}\">Open</a></p>"
        ),
        ctx=ctx,
    )
