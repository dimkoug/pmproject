"""Operational maintenance Celery tasks: audit retention (#21), postgres
backup (#23), and backup pruning.

All three run on the `reports` queue because they can be slow / I/O heavy.
Schedules live in `app/celery_app.py::beat_schedule`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.celery_app import celery
from app.config import settings

logger = logging.getLogger(__name__)


# ─── Audit retention ─────────────────────────────────────────────

@celery.task(name="purge_old_audit_task", bind=True, max_retries=1)
def purge_old_audit_task(self):
    """DELETE audit entries older than settings.audit_retention_days.
    Runs in its own event loop via asyncio.run because Celery's prefork pool
    doesn't give us one."""
    async def _run():
        from sqlalchemy import text
        from app.database import engine
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
        async with engine.begin() as conn:
            r = await conn.execute(
                text("DELETE FROM audit_entries WHERE created_at < :c"),
                {"c": cutoff},
            )
            return r.rowcount or 0
    try:
        deleted = asyncio.run(_run())
        logger.info("Audit retention purge: deleted %s rows older than %sd", deleted, settings.audit_retention_days)
        return {"deleted": deleted, "cutoff_days": settings.audit_retention_days}
    except Exception as exc:
        logger.exception("Audit purge failed")
        raise self.retry(exc=exc, countdown=60)


# ─── Postgres backup ─────────────────────────────────────────────

def _parse_db_url(url: str) -> dict[str, str]:
    """Parse a SQLAlchemy async URL into pg_dump arg dict."""
    # e.g. postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject
    from urllib.parse import urlparse
    u = urlparse(url.replace("+asyncpg", ""))
    return {
        "host": u.hostname or "",
        "port": str(u.port or 5432),
        "user": u.username or "",
        "password": u.password or "",
        "db": (u.path or "/").lstrip("/"),
    }


@celery.task(name="pg_backup_task", bind=True, max_retries=2)
def pg_backup_task(self):
    """Dump the primary Postgres via pg_dump to `BACKUP_DIR`.
    Returns the dump path + compressed size. Requires `pg_dump` in the worker
    image (use postgres-client in the Dockerfile if you're not already)."""
    try:
        Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)
        cfg = _parse_db_url(settings.database_url)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path(settings.backup_dir) / f"{cfg['db']}-{stamp}.sql.gz"
        env = {**os.environ, "PGPASSWORD": cfg["password"]}
        # Use custom format + gzip; drop large indexes during restore if you want
        # faster recovery (not added here to keep the backup identical to prod).
        with open(out_path, "wb") as out_f:
            dump = subprocess.Popen(
                [
                    "pg_dump",
                    "-h", cfg["host"],
                    "-p", cfg["port"],
                    "-U", cfg["user"],
                    "-d", cfg["db"],
                    "--no-owner", "--no-acl", "--format=plain",
                ],
                stdout=subprocess.PIPE,
                env=env,
            )
            gz = subprocess.Popen(["gzip", "-9"], stdin=dump.stdout, stdout=out_f)
            dump.stdout.close()  # type: ignore
            gz.communicate()
            dump.wait()
            if dump.returncode != 0:
                raise RuntimeError(f"pg_dump exited {dump.returncode}")
        size = out_path.stat().st_size
        logger.info("Backup written: %s (%s bytes)", out_path, size)
        return {"path": str(out_path), "bytes": size, "ok": True}
    except FileNotFoundError:
        logger.warning("pg_dump not found in this worker image — skipping backup. Install postgres-client.")
        return {"skipped": True, "reason": "pg_dump not installed"}
    except Exception as exc:
        logger.exception("pg_backup_task failed")
        raise self.retry(exc=exc, countdown=300)


# ─── Webhook retry sweeper (#8) ─────────────────────────────────

@celery.task(name="retry_webhook_deliveries_task", bind=True, max_retries=1)
def retry_webhook_deliveries_task(self):
    """Pick up any WebhookDelivery rows whose next_attempt_at is due and
    retry them. Runs every minute on beat."""
    async def _run():
        from app.services.webhooks import retry_pending_deliveries
        return await retry_pending_deliveries(batch_size=100)
    try:
        result = asyncio.run(_run())
        if result.get("examined", 0) > 0:
            logger.info("webhook retry sweep: %s", result)
        return result
    except Exception as exc:
        logger.exception("retry_webhook_deliveries_task failed")
        raise self.retry(exc=exc, countdown=30)


@celery.task(name="purge_old_backups_task", bind=True, max_retries=1)
def purge_old_backups_task(self):
    """Remove backup files older than settings.backup_retention_days."""
    try:
        root = Path(settings.backup_dir)
        if not root.exists():
            return {"deleted": 0, "note": "backup dir does not exist"}
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.backup_retention_days)
        deleted = 0
        total_bytes = 0
        for p in root.glob("*.sql.gz"):
            try:
                if datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) < cutoff:
                    total_bytes += p.stat().st_size
                    p.unlink()
                    deleted += 1
            except Exception:
                logger.warning("Failed to unlink %s", p, exc_info=True)
        logger.info("Backup purge: removed %s files (%s bytes)", deleted, total_bytes)
        return {"deleted": deleted, "bytes_freed": total_bytes}
    except Exception as exc:
        logger.exception("purge_old_backups_task failed")
        raise self.retry(exc=exc, countdown=60)
