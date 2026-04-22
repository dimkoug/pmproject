"""Celery tasks for DMS: expiry reminders, retention auto-run.

Celery workers are sync processes, but the project uses async SQLAlchemy.
We bridge by running an inner async coroutine with asyncio.run().
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_

from app.celery_app import celery

logger = logging.getLogger(__name__)


# ── Expiry reminders ──────────────────────────────────────────────


async def _run_expiry_reminders(days_ahead: int) -> dict:
    from app.database import async_session
    from app.models.dms import Document
    from app.models.notification import Notification
    from app.models.user import User

    cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    created = 0
    emailed = 0
    async with async_session() as db:
        q = select(Document).where(
            Document.expiry_date.is_not(None),
            Document.expiry_date <= cutoff,
            Document.expiry_date >= datetime.now(timezone.utc),
        )
        for doc in (await db.scalars(q)).all():
            if not doc.created_by_id:
                continue
            # Don't double-notify: check for an existing unread notification
            # for the same doc in the last 24 hours.
            recent_title = f"Document expiring: {doc.title}"
            existing = await db.scalar(
                select(Notification.id).where(
                    and_(
                        Notification.user_id == doc.created_by_id,
                        Notification.title == recent_title,
                        Notification.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                    )
                )
            )
            if existing:
                continue

            days_left = (doc.expiry_date - datetime.now(timezone.utc)).days
            db.add(Notification(
                user_id=doc.created_by_id,
                project_id=doc.project_id,
                title=recent_title,
                body=f"Expires in {days_left} day{'s' if days_left != 1 else ''} ({doc.expiry_date.date()}).",
                link=f"/documents",
            ))
            created += 1

            # Also email the document owner
            user = await db.get(User, doc.created_by_id)
            if user and user.email:
                from app.services.email import queue_expiry_reminder
                queue_expiry_reminder(user.email, doc.title, days_left, str(doc.expiry_date.date()))
                emailed += 1
        await db.commit()
    return {"notifications_created": created, "emails_queued": emailed, "days_ahead": days_ahead}


@celery.task(name="run_expiry_reminders_task", bind=True, max_retries=1)
def run_expiry_reminders_task(self, days_ahead: int = 7):
    """Scan for documents expiring within N days and create notifications."""
    try:
        return asyncio.run(_run_expiry_reminders(days_ahead))
    except Exception as exc:
        logger.exception("Expiry reminder task failed")
        raise self.retry(exc=exc, countdown=60)


# ── Retention auto-run ───────────────────────────────────────────


async def _run_retention() -> dict:
    from app.database import async_session
    from app.models.dms import Document, DocumentStatus, RetentionPolicy, RetentionAction

    archived = 0
    deleted = 0
    async with async_session() as db:
        policies = (await db.scalars(
            select(RetentionPolicy).where(RetentionPolicy.is_active == True)  # noqa: E712
        )).all()
        now = datetime.now(timezone.utc)
        for pol in policies:
            cutoff = now - timedelta(days=pol.days_after)
            q = select(Document).where(Document.updated_at <= cutoff)
            if pol.folder_id:
                q = q.where(Document.folder_id == pol.folder_id)
            if pol.tag_match:
                q = q.where(Document.tags.ilike(f"%{pol.tag_match}%"))
            for doc in (await db.scalars(q)).all():
                if pol.action == RetentionAction.ARCHIVE:
                    if doc.status != DocumentStatus.ARCHIVED:
                        doc.status = DocumentStatus.ARCHIVED
                        archived += 1
                elif pol.action == RetentionAction.DELETE:
                    await db.delete(doc)
                    deleted += 1
        await db.commit()
    return {"archived": archived, "deleted": deleted}


@celery.task(name="run_retention_task", bind=True, max_retries=1)
def run_retention_task(self):
    """Apply all active retention policies."""
    try:
        return asyncio.run(_run_retention())
    except Exception as exc:
        logger.exception("Retention task failed")
        raise self.retry(exc=exc, countdown=60)
