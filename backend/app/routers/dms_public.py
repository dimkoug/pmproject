"""Public DMS endpoints — no auth required. Only serves valid share-link tokens."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.dms import Document, DocumentVersion, DocumentShareLink
from app.services.storage import get_storage

# NOTE: no get_current_user dep — this is public by design.
router = APIRouter(prefix="/api/dms", tags=["dms_public"])


@router.get("/share/{token}")
async def public_download(token: str, db: AsyncSession = Depends(get_db)):
    link = (await db.scalars(select(DocumentShareLink).where(DocumentShareLink.token == token))).first()
    if not link or link.is_revoked:
        raise HTTPException(404, "Link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "Link expired")

    doc = await db.get(Document, link.document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    ver = (await db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )).first()
    if not ver:
        raise HTTPException(404, "Version not found")

    path = get_storage().get_path(ver.filename)
    if not path:
        raise HTTPException(404, "File not found on storage")

    link.download_count = link.download_count + 1
    await db.commit()
    return FileResponse(path, filename=ver.original_name, media_type=ver.content_type)
