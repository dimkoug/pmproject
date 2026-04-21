"""Minimal additive migration helper — runs idempotent ALTER TABLE statements
on startup. We're not using Alembic (yet); this lives alongside Base.metadata.create_all
to cover columns added to existing tables.

Each statement uses `ADD COLUMN IF NOT EXISTS` (Postgres 9.6+) so re-running is safe.
"""

import logging

from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)


# ── Additive migrations ───────────────────────────────────────────────
# Format: "<description>": "SQL statement"
MIGRATIONS: dict[str, str] = {
    "dms_documents.expiry_date":
        "ALTER TABLE dms_documents ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMPTZ",
}


async def run_additive_migrations() -> None:
    async with engine.begin() as conn:
        for label, sql in MIGRATIONS.items():
            try:
                await conn.execute(text(sql))
            except Exception:
                logger.warning("Migration failed for %s", label, exc_info=True)
