"""Transactional email delivery.

Two layers:
  * `send_email_now()` — blocking SMTP send, intended only for testing/debug.
  * `send_email_task` — Celery task (reports queue) that the app calls instead,
    so request handlers don't block on SMTP.

When `SMTP_HOST` is unset the email layer logs the would-have-been message and
returns quietly — lets you develop locally without real email delivery.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.celery_app import celery
from app.config import settings

logger = logging.getLogger(__name__)


def send_email_now(to: str, subject: str, body_text: str, body_html: str | None = None) -> None:
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
def send_email_task(self, to: str, subject: str, body_text: str, body_html: str | None = None):
    try:
        send_email_now(to, subject, body_text, body_html)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ── Convenience wrappers used throughout the app ────────────────────

def queue_password_reset(to: str, reset_token: str, user_name: str | None = None):
    link = f"{settings.app_base_url}/reset-password?token={reset_token}"
    send_email_task.delay(
        to=to,
        subject="Reset your password",
        body_text=f"Hi {user_name or ''},\n\nUse this link to reset your password:\n{link}\n\nIt expires in 1 hour.",
        body_html=(
            f"<p>Hi {user_name or ''},</p>"
            f"<p>Use this link to reset your password:</p>"
            f"<p><a href='{link}'>{link}</a></p>"
            f"<p>It expires in 1 hour.</p>"
        ),
    )


def queue_signature_request(to: str, document_title: str, token: str, message: str | None = None):
    link = f"{settings.app_base_url}/sign/{token}"
    send_email_task.delay(
        to=to,
        subject=f"Signature requested: {document_title}",
        body_text=f"You have been asked to sign the document '{document_title}'.\n\n{message or ''}\n\nOpen it here:\n{link}",
        body_html=(
            f"<p>You have been asked to sign the document <strong>{document_title}</strong>.</p>"
            f"<p>{message or ''}</p>"
            f"<p><a href='{link}'>Open document to sign</a></p>"
        ),
    )


def queue_approval_assigned(to: str, target_type: str, note: str | None = None):
    send_email_task.delay(
        to=to,
        subject=f"Approval required: {target_type}",
        body_text=f"An approval request is waiting for you.\n\nType: {target_type}\nNote: {note or '—'}\n\n{settings.app_base_url}/admin",
        body_html=(
            f"<p>An approval request is waiting for you.</p>"
            f"<p><strong>Type:</strong> {target_type}<br><strong>Note:</strong> {note or '—'}</p>"
            f"<p><a href='{settings.app_base_url}/admin'>Open approvals inbox</a></p>"
        ),
    )


def queue_expiry_reminder(to: str, doc_title: str, days_left: int, expiry_date: str):
    send_email_task.delay(
        to=to,
        subject=f"Document expiring: {doc_title}",
        body_text=f"'{doc_title}' expires in {days_left} day{'s' if days_left != 1 else ''} ({expiry_date}).\n\n{settings.app_base_url}/documents",
        body_html=(
            f"<p><strong>{doc_title}</strong> expires in {days_left} day{'s' if days_left != 1 else ''} "
            f"({expiry_date}).</p>"
            f"<p><a href='{settings.app_base_url}/documents'>View document</a></p>"
        ),
    )


def queue_mention_notification(to: str, actor_name: str, context: str, link: str):
    send_email_task.delay(
        to=to,
        subject=f"{actor_name} mentioned you",
        body_text=f"{actor_name} mentioned you in {context}.\n\nOpen: {settings.app_base_url}{link}",
        body_html=(
            f"<p>{actor_name} mentioned you in {context}.</p>"
            f"<p><a href='{settings.app_base_url}{link}'>Open</a></p>"
        ),
    )
