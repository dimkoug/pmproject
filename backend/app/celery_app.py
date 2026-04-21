"""Celery application — broker & result backend both backed by Redis.

Two queues:
  * `default` — lightweight async work (CSV parsing, quick imports).
  * `reports` — slow/CPU-heavy jobs (PDF generation, Monte Carlo, scheduled
    report runs, depreciation batches). Served by the dedicated
    `celery-reports` worker so a long PDF render never blocks short tasks.
"""

from celery import Celery
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
    },
)

# Auto-discover tasks from app.tasks module
celery.autodiscover_tasks(["app"])
