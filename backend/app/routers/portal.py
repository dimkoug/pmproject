"""Customer portal (#74).

Two surfaces:

  * Admin-side magic-link generation (auth required, requires
    `sales.company.manage`):
      POST /api/admin/portal/magic-link  → returns the URL the admin shares.
      GET  /api/admin/portal/tokens?company_id=  → recent tokens for a company.

  * Customer-side portal (no internal-user auth — uses portal-scoped JWT):
      POST /api/portal/exchange?token=...  → trade magic token for portal JWT.
      GET  /api/portal/me                  → company info.
      GET  /api/portal/invoices            → invoices for this company.
      POST /api/portal/invoices/{id}/checkout → Stripe session, scoped to this company.

The portal JWT carries `kind="portal"` + `company_id` and is short-lived.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.crm import Company
from app.models.erp import Invoice, InvoiceStatus, InvoiceType
from app.models.portal import PortalToken
from app.models.user import User

# Admin sub-router (require login + permission)
admin_router = APIRouter(prefix="/api/admin/portal", tags=["portal-admin"], dependencies=[Depends(get_current_user)])

# Customer-facing sub-router (NO get_current_user dep — uses portal JWT)
public_router = APIRouter(prefix="/api/portal", tags=["portal"])

PORTAL_JWT_TTL_MIN = 60
PORTAL_JWT_KIND = "portal"


# ── Magic link admin side ──────────────────────────────────────────

class MagicLinkRequest(BaseModel):
    company_id: UUID
    label: str | None = None
    expires_in_hours: int = 168  # 7 days default


def _portal_link(token: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/portal/login?t={token}"


@admin_router.post("/magic-link", dependencies=[Depends(require_permission("sales.company.manage"))])
async def create_magic_link(p: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, p.company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    expires = datetime.utcnow() + timedelta(hours=max(1, p.expires_in_hours))
    raw = secrets.token_urlsafe(32)
    pt = PortalToken(
        company_id=p.company_id,
        token=raw,
        label=p.label,
        expires_at=expires,
    )
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    return {
        "id": str(pt.id),
        "url": _portal_link(raw),
        "expires_at": pt.expires_at.isoformat(),
        "company_name": company.name,
    }


@admin_router.get("/tokens", dependencies=[Depends(require_permission("sales.company.manage"))])
async def list_tokens(company_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(PortalToken).where(PortalToken.company_id == company_id).order_by(PortalToken.created_at.desc()).limit(50)
    )
    return [
        {
            "id": str(t.id),
            "label": t.label,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "used_at": t.used_at.isoformat() if t.used_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in r.scalars().all()
    ]


# ── Portal session ──────────────────────────────────────────────────

class ExchangeRequest(BaseModel):
    token: str


def _make_portal_jwt(company_id: UUID) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(company_id),
        "kind": PORTAL_JWT_KIND,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=PORTAL_JWT_TTL_MIN)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _verify_portal_jwt(token: str) -> UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(401, "Invalid portal session")
    if payload.get("kind") != PORTAL_JWT_KIND:
        raise HTTPException(401, "Wrong token kind")
    company_id = payload.get("sub")
    if not company_id:
        raise HTTPException(401, "Malformed portal token")
    try:
        return UUID(company_id)
    except Exception:
        raise HTTPException(401, "Bad company id")


async def get_portal_company(
    authorization: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Company:
    """Dependency that pulls the Company from the portal Authorization header."""
    from fastapi import Header
    raise NotImplementedError  # never called — see _resolve_portal_company below


async def _resolve_portal_company(
    authorization: str | None,
    db: AsyncSession,
) -> Company:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing portal bearer token")
    company_id = _verify_portal_jwt(authorization.split(" ", 1)[1])
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(401, "Company no longer exists")
    return company


from fastapi import Header  # placed after to avoid linter complaining about top-of-file unused import


@public_router.post("/exchange")
async def exchange_token(p: ExchangeRequest, db: AsyncSession = Depends(get_db)):
    """Swap a magic-link token for a short-lived portal JWT."""
    r = await db.execute(select(PortalToken).where(PortalToken.token == p.token))
    pt = r.scalar_one_or_none()
    if not pt:
        raise HTTPException(401, "Invalid token")
    if pt.expires_at and pt.expires_at < datetime.utcnow():
        raise HTTPException(401, "Token expired")
    if pt.used_at:
        # Single-use; if you want re-use, comment this out
        raise HTTPException(401, "Token already used")
    pt.used_at = datetime.utcnow()
    await db.commit()
    company = await db.get(Company, pt.company_id)
    if not company:
        raise HTTPException(404, "Company missing")
    return {
        "access_token": _make_portal_jwt(pt.company_id),
        "token_type": "bearer",
        "expires_in_minutes": PORTAL_JWT_TTL_MIN,
        "company": {"id": str(company.id), "name": company.name},
    }


@public_router.get("/me")
async def portal_me(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    company = await _resolve_portal_company(authorization, db)
    return {"id": str(company.id), "name": company.name, "industry": company.industry, "website": company.website}


@public_router.get("/invoices")
async def portal_invoices(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    company = await _resolve_portal_company(authorization, db)
    r = await db.execute(
        select(Invoice).where(
            Invoice.company_id == company.id,
            Invoice.invoice_type == InvoiceType.RECEIVABLE,
        ).order_by(Invoice.issue_date.desc()).limit(200)
    )
    out = []
    for i in r.scalars().all():
        out.append({
            "id": str(i.id),
            "invoice_number": i.invoice_number,
            "status": i.status.value,
            "issue_date": i.issue_date.isoformat()[:10] if i.issue_date else None,
            "due_date": i.due_date.isoformat()[:10] if i.due_date else None,
            "subtotal": i.subtotal,
            "tax_amount": i.tax_amount,
            "total": i.total,
            "paid_amount": i.paid_amount,
            "currency": i.currency,
            "outstanding": round((i.total or 0) - (i.paid_amount or 0), 2),
        })
    return out


@public_router.post("/invoices/{invoice_id}/checkout")
async def portal_checkout(
    invoice_id: UUID,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    company = await _resolve_portal_company(authorization, db)
    inv = await db.get(Invoice, invoice_id)
    if not inv or inv.company_id != company.id:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.PAID:
        raise HTTPException(400, "Already paid")
    outstanding = round((inv.total or 0.0) - (inv.paid_amount or 0.0), 2)
    if outstanding <= 0:
        raise HTTPException(400, "No outstanding balance")
    from app.services.stripe_client import create_checkout_session, is_configured
    if not is_configured():
        raise HTTPException(503, "Stripe not configured")
    base = settings.app_base_url.rstrip("/")
    success = f"{base}/portal?paid={inv.id}"
    cancel = f"{base}/portal?cancelled={inv.id}"
    try:
        session = await create_checkout_session(
            invoice_id=str(inv.id),
            invoice_number=inv.invoice_number,
            amount_due=outstanding,
            currency=inv.currency,
            success_url=success,
            cancel_url=cancel,
        )
    except Exception as e:
        raise HTTPException(502, f"Stripe error: {e}")
    inv.stripe_session_id = session.get("id")
    await db.commit()
    return {"url": session.get("url"), "session_id": session.get("id")}
