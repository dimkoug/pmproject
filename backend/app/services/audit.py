"""Audit logging helper — writes `AuditEntry` rows so every sensitive action
across the system lands in the global audit trail visible from /admin/audit.

Usage:

    from app.services.audit import log_audit
    await log_audit(db, user, domain="dms", action="download", entity_type="document", entity_id=str(doc.id))

Swallows exceptions so a broken audit write never fails the primary request —
the primary action already succeeded when we log.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cross import AuditEntry
from app.models.user import User

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    user: User | None,
    *,
    domain: str,
    action: str,
    entity_type: str,
    entity_id: str | UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    try:
        entry = AuditEntry(
            user_id=user.id if user else None,
            domain=domain,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_data=json.dumps(before, default=str) if before else None,
            after_data=json.dumps(after, default=str) if after else None,
            ip=ip,
        )
        db.add(entry)
        # Don't commit here — let the caller's transaction batch it.
    except Exception:
        logger.warning("Audit log failed for %s/%s", domain, action, exc_info=True)
