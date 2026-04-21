import os
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attachment import Attachment
from app.models.user import User

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api/attachments", tags=["attachments"], dependencies=[Depends(get_current_user)])


@router.get("/")
async def list_attachments(target_type: str, target_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Attachment)
        .where(Attachment.target_type == target_type, Attachment.target_id == target_id)
        .order_by(Attachment.created_at.desc())
    )
    return [
        {
            "id": str(a.id), "original_name": a.original_name,
            "content_type": a.content_type, "size_bytes": a.size_bytes,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.post("/", status_code=201)
async def upload_attachment(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    target_type: str = Form(...),
    target_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_id = str(uuid_mod.uuid4())
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{file_id}{ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)

    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    att = Attachment(
        project_id=UUID(project_id),
        user_id=current_user.id,
        target_type=target_type,
        target_id=UUID(target_id),
        filename=stored_name,
        original_name=file.filename or "file",
        content_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return {"id": str(att.id), "original_name": att.original_name, "size_bytes": att.size_bytes}


@router.get("/{attachment_id}/download")
async def download_attachment(attachment_id: UUID, db: AsyncSession = Depends(get_db)):
    att = await db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = os.path.join(UPLOAD_DIR, att.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path, filename=att.original_name, media_type=att.content_type)


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(attachment_id: UUID, db: AsyncSession = Depends(get_db)):
    att = await db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = os.path.join(UPLOAD_DIR, att.filename)
    if os.path.exists(path):
        os.remove(path)
    await db.delete(att)
    await db.commit()
