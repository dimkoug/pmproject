"""Soft-delete admin router (#7 / #22).

Serves as the inverse of the flagship DELETE endpoints that now soft-delete
instead of hard-deleting. Lists trashed rows across entity types, lets
admins restore them, and permanently purges a row (the only destructive
operation).

Supported entities in phase 1: project, company, invoice, document. Each
has a `deleted_at` column + partial index. Adding more is mechanical:
register the `(entity, Model)` tuple below.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.crm import Company
from app.models.dms import Document
from app.models.erp import Invoice
from app.models.project import Project

router = APIRouter(prefix="/api/admin/trash", tags=["trash"], dependencies=[Depends(get_current_user)])


ENTITY_MODELS = {
    "project": Project,
    "company": Company,
    "invoice": Invoice,
    "document": Document,
}


def _title_for(entity: str, row) -> str:
    return (
        getattr(row, "name", None)
        or getattr(row, "title", None)
        or getattr(row, "invoice_number", None)
        or str(row.id)
    )


@router.get("", dependencies=[Depends(require_permission("admin.audit.view"))])
async def list_trash(
    entity: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List trashed rows across supported entities. Filter to one with ?entity=."""
    out: list[dict] = []
    targets = {entity: ENTITY_MODELS[entity]} if entity and entity in ENTITY_MODELS else ENTITY_MODELS
    for ent, Model in targets.items():
        r = await db.execute(
            select(Model).where(Model.deleted_at.is_not(None)).order_by(Model.deleted_at.desc()).limit(limit)
        )
        for row in r.scalars().all():
            out.append({
                "entity": ent,
                "id": str(row.id),
                "title": _title_for(ent, row),
                "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
            })
    out.sort(key=lambda e: e["deleted_at"] or "", reverse=True)
    return out[:limit]


@router.post("/{entity}/{row_id}/restore", dependencies=[Depends(require_permission("admin.audit.view"))])
async def restore_row(entity: str, row_id: UUID, db: AsyncSession = Depends(get_db)):
    if entity not in ENTITY_MODELS:
        raise HTTPException(404, "Unknown entity")
    Model = ENTITY_MODELS[entity]
    row = await db.get(Model, row_id)
    if not row:
        raise HTTPException(404, f"{entity} not found")
    if row.deleted_at is None:
        raise HTTPException(400, f"{entity} is not trashed")
    row.deleted_at = None
    await db.commit()
    return {"entity": entity, "id": str(row.id), "restored": True}


@router.delete("/{entity}/{row_id}", status_code=204, dependencies=[Depends(require_permission("admin.user.manage"))])
async def purge_row(entity: str, row_id: UUID, db: AsyncSession = Depends(get_db)):
    """Permanently delete a trashed row. Requires `admin.user.manage` since
    this is the only destructive operation left after soft-delete."""
    if entity not in ENTITY_MODELS:
        raise HTTPException(404, "Unknown entity")
    Model = ENTITY_MODELS[entity]
    row = await db.get(Model, row_id)
    if not row:
        raise HTTPException(404, f"{entity} not found")
    if row.deleted_at is None:
        raise HTTPException(400, "Can only purge rows that are already trashed")
    await db.delete(row)
    await db.commit()


# Also add Project model + migration — used to demonstrate the flow from
# existing DELETE endpoint. Other entities: model already has deleted_at via
# ALTER, but their DELETE endpoints still hard-delete; refactoring them is
# mechanical follow-up (flip `await db.delete(row)` to `row.deleted_at =
# datetime.now(timezone.utc)`).

_ = datetime  # keep import referenced
