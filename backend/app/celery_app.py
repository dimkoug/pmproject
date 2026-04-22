"""Celery application — broker & result backend both backed by Redis.

Two queues:
  * `default` — lightweight async work (CSV parsing, quick imports).
  * `reports` — slow/CPU-heavy jobs (PDF generation, Monte Carlo, scheduled
    report runs, depreciation batches, nightly retention / expiry scans).
    Served by the dedicated `celery-reports` worker so a long PDF render
    never blocks short tasks.
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

celery = Celery(
    "pmproject",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Limit prefetch so long tasks don't starve workers
    worker_prefetch_multiplier=2,
    # Result expiry: 1 hour
    result_expires=3600,
    # Retry broker connection on startup
    broker_connection_retry_on_startup=True,
    # Queues
    task_queues=(
        Queue("default"),
        Queue("reports"),
    ),
    task_default_queue="default",
    # Route heavy jobs to the reports worker.
    task_routes={
        "run_monte_carlo_task": {"queue": "reports"},
        "generate_pdf_report_task": {"queue": "reports"},
        "run_scheduled_reports_task": {"queue": "reports"},
        "run_depreciation_task": {"queue": "reports"},
        "run_recurring_invoices_task": {"queue": "reports"},
        "run_expiry_reminders_task": {"queue": "reports"},
        "run_retention_task": {"queue": "reports"},
        "send_email_task": {"queue": "reports"},
        "purge_old_audit_task": {"queue": "reports"},
        "pg_backup_task": {"queue": "reports"},
        "purge_old_backups_task": {"queue": "reports"},
        "retry_webhook_deliveries_task": {"queue": "default"},
    },
    # Celery Beat schedule — nightly housekeeping.
    beat_schedule={
        "dms-expiry-reminders": {
            "task": "run_expiry_reminders_task",
            "schedule": crontab(minute=0, hour=1),   # 01:00 UTC daily
            "kwargs": {"days_ahead": 7},
        },
        "dms-retention": {
            "task": "run_retention_task",
            "schedule": crontab(minute=0, hour=2),   # 02:00 UTC daily
        },
        "purge-old-audit": {
            "task": "purge_old_audit_task",
            "schedule": crontab(minute=15, hour=3),  # 03:15 UTC daily (#21)
        },
        "pg-backup": {
            "task": "pg_backup_task",
            "schedule": crontab(minute=0, hour=0),   # 00:00 UTC daily (#23)
        },
        "purge-old-backups": {
            "task": "purge_old_backups_task",
            "schedule": crontab(minute=30, hour=0),  # 00:30 UTC daily
        },
        # Webhook retry sweeper (#8) — every minute. Cheap: a single indexed
        # query against webhook_deliveries where next_attempt_at <= now.
        "retry-webhook-deliveries": {
            "task": "retry_webhook_deliveries_task",
            "schedule": 60.0,
        },
    },
)

# Auto-discover tasks from app.tasks and app.tasks_dms modules
celery.autodiscover_tasks(["app"])
# Explicit import so the task module is registered on worker startup
import app.tasks_dms  # noqa: F401, E402
import app.services.email  # noqa: F401, E402  (registers send_email_task)
import app.tasks_ops  # noqa: F401, E402  (registers audit purge, backup, backup-purge tasks)
