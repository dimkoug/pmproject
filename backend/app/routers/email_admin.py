"""Email templates admin + open/click tracking endpoints (#6, #7)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import EmailTemplate, EmailTrackingEvent

# A 1×1 transparent GIF — smallest valid image payload we can serve as an open pixel.
_PIXEL = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")


# ── Admin CRUD on templates ────────────────────────────────────────

admin_router = APIRouter(prefix="/api/admin/email-templates",
                         tags=["email-templates"],
                         dependencies=[Depends(get_current_user)])


class TemplateIn(BaseModel):
    key: str
    subject: str
    body_text: str
    body_html: str | None = None


@admin_router.get("")
async def list_templates(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EmailTemplate).order_by(EmailTemplate.key))).scalars().all()
    return [{"id": str(t.id), "key": t.key, "subject": t.subject, "updated_at": t.updated_at.isoformat()} for t in rows]


@admin_router.post("", status_code=201, dependencies=[Depends(require_permission("admin.email.manage"))])
async def create_template(p: TemplateIn, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(EmailTemplate).where(EmailTemplate.key == p.key))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Template with this key already exists")
    t = EmailTemplate(key=p.key, subject=p.subject, body_text=p.body_text, body_html=p.body_html)
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id": str(t.id), "key": t.key}


@admin_router.get("/{key}")
async def get_template(key: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(EmailTemplate).where(EmailTemplate.key == key))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Template not found")
    return {"id": str(row.id), "key": row.key, "subject": row.subject,
            "body_text": row.body_text, "body_html": row.body_html,
            "updated_at": row.updated_at.isoformat()}


@admin_router.patch("/{template_id}", dependencies=[Depends(require_permission("admin.email.manage"))])
async def update_template(template_id: UUID, p: TemplateIn, db: AsyncSession = Depends(get_db)):
    row = await db.get(EmailTemplate, template_id)
    if not row:
        raise HTTPException(404, "Template not found")
    row.subject = p.subject
    row.body_text = p.body_text
    row.body_html = p.body_html
    await db.commit()
    return {"id": str(row.id), "key": row.key}


@admin_router.delete("/{template_id}", status_code=204, dependencies=[Depends(require_permission("admin.email.manage"))])
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(EmailTemplate, template_id)
    if not row:
        raise HTTPException(404, "Template not found")
    await db.delete(row); await db.commit()


# ── Tracking — no auth; beacon-style endpoints ────────────────────

track_router = APIRouter(prefix="/api/t", tags=["email-tracking"])


async def _record(db: AsyncSession, request: Request, event_type: str,
                  recipient: str | None, template_key: str | None, url: str | None) -> None:
    try:
        evt = EmailTrackingEvent(
            recipient=(recipient or "")[:255],
            template_key=(template_key or None),
            event_type=event_type,
            url=(url or None),
            ua=(request.headers.get("user-agent") or "")[:500] or None,
            ip=(request.client.host if request.client else None),
        )
        db.add(evt); await db.commit()
    except Exception:
        # Never let a tracking failure break the user's link click.
        await db.rollback()


@track_router.get("/open/{event_id}.gif")
async def track_open(event_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    r = request.query_params.get("r")
    k = request.query_params.get("k")
    await _record(db, request, "open", r, k, None)
    return Response(content=_PIXEL, media_type="image/gif",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})


@track_router.get("/click/{event_id}")
async def track_click(event_id: str, request: Request, u: str, db: AsyncSession = Depends(get_db)):
    r = request.query_params.get("r")
    k = request.query_params.get("k")
    await _record(db, request, "click", r, k, u)
    return RedirectResponse(url=u, status_code=302)


@track_router.get("/stats")
async def email_stats(db: AsyncSession = Depends(get_db),
                      _: object = Depends(require_permission("admin.email.manage"))):
    """Aggregate: sent / open / click counts per template_key."""
    from sqlalchemy import func
    rows = (await db.execute(
        select(EmailTrackingEvent.template_key, EmailTrackingEvent.event_type,
               func.count(EmailTrackingEvent.id))
        .group_by(EmailTrackingEvent.template_key, EmailTrackingEvent.event_type)
    )).all()
    out: dict[str, dict[str, int]] = {}
    for key, event, count in rows:
        k = key or "(none)"
        out.setdefault(k, {"open": 0, "click": 0, "sent": 0})
        out[k][event] = int(count)
    return out
