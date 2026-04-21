"""Celery application — broker & result backend both backed by Redis."""

from celery import Celery

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
)

# Auto-discover tasks from app.tasks module
celery.autodiscover_tasks(["app"])
