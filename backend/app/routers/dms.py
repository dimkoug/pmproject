"""Document Management System: Folders, Documents with version control, search, tags, signatures, templates, ACL, retention, entity links."""

import os
import re
import secrets
import uuid as uuid_mod
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import UserRole
from app.services.audit import log_audit
from app.services.storage import get_storage


async def _restricted_folder_ids(db: AsyncSession) -> set:
    """Return the set of folder IDs that have at least one FolderPermission row.
    Those folders are treated as private — visible only to users listed in them.
    Folders with no rows are shared by default."""
    rows = await db.execute(select(FolderPermission.folder_id).distinct())
    return {r for r in rows.scalars().all()}


async def _user_folder_ids(db: AsyncSession, user_id) -> set:
    """Folder IDs the given user has an explicit permission on."""
    rows = await db.execute(
        select(FolderPermission.folder_id).where(FolderPermission.user_id == user_id)
    )
    return {r for r in rows.scalars().all()}


async def _can_see_folder(db: AsyncSession, user, folder) -> bool:
    """True if user can see the folder per FolderPermission rules."""
    if user.role == UserRole.ADMIN:
        return True
    if folder.created_by_id == user.id:
        return True
    restricted = await _restricted_folder_ids(db)
    if folder.id not in restricted:
        return True  # public/shared
    allowed = await _user_folder_ids(db, user.id)
    return folder.id in allowed
from app.models.dms import (
    Document, DocumentStatus, DocumentVersion, Folder,
    SignatureRequest, SignatureRequestStatus, DocumentTemplate,
    FolderPermission, RetentionPolicy, RetentionAction, EntityLink, EntityType,
    DocumentLock, DocumentWorkflow, WorkflowStep, WorkflowStepStatus,
    DocumentAnnotation, ESignProvider, ESignProviderType, ScanResult, ScanStatus,
    DocumentShareLink,
)
from app.models.user import User


def _ocr_image(content: bytes) -> str | None:
    """OCR an image with Tesseract. Returns None on any error."""
    try:
        import io
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
        img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(img)[:200000]
    except Exception:
        return None


def _ocr_pdf(content: bytes) -> str | None:
    """Rasterise a PDF with pdf2image and OCR each page."""
    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_bytes  # type: ignore
        images = convert_from_bytes(content, dpi=200)
        return "\n".join(pytesseract.image_to_string(img) for img in images)[:200000]
    except Exception:
        return None


def extract_text(content: bytes, content_type: str | None, filename: str) -> str | None:
    """Best-effort text extraction. Returns plain text or None.

    Plain-text / markdown / csv / json / html — decode directly.
    PDF — try pypdf first; if that yields nothing and OCR is enabled, rasterise
    and run Tesseract over each page (slow, but handles scanned PDFs).
    Images — Tesseract OCR when DMS_OCR_ENABLED=1.
    """
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    ocr_on = os.environ.get("DMS_OCR_ENABLED") == "1"

    try:
        if ct.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".json", ".html", ".xml", ".log")):
            return content.decode("utf-8", errors="ignore")[:200000]

        if ct == "application/pdf" or name.endswith(".pdf"):
            try:
                from pypdf import PdfReader  # type: ignore
                import io
                reader = PdfReader(io.BytesIO(content))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)[:200000]
                if text.strip():
                    return text
                # Fallback to OCR for scanned PDFs with no embedded text
                if ocr_on:
                    return _ocr_pdf(content)
            except Exception:
                if ocr_on:
                    return _ocr_pdf(content)
                return None

        if ocr_on and (ct.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"))):
            return _ocr_image(content)
    except Exception:
        return None
    return None

UPLOAD_DIR = "/app/uploads/dms"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api/dms", tags=["dms"], dependencies=[Depends(get_current_user)])


# ── Folders ─────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    project_id: UUID | None = None; parent_id: UUID | None = None; name: str; description: str | None = None

@router.get("/folders")
async def list_folders(project_id: UUID | None = None, parent_id: UUID | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Folder).order_by(Folder.name)
    if project_id: q = q.where(Folder.project_id == project_id)
    if parent_id: q = q.where(Folder.parent_id == parent_id)
    else: q = q.where(Folder.parent_id.is_(None))
    result = await db.execute(q)
    # Folder visibility: admin bypass, creator bypass, otherwise must either
    # be a shared folder (no FolderPermission rows) or have an explicit grant.
    restricted = await _restricted_folder_ids(db) if current_user.role != UserRole.ADMIN else set()
    allowed = await _user_folder_ids(db, current_user.id) if current_user.role != UserRole.ADMIN else set()
    folders = []
    for f in result.scalars().all():
        if current_user.role != UserRole.ADMIN and f.created_by_id != current_user.id:
            if f.id in restricted and f.id not in allowed:
                continue
        doc_count = await db.scalar(select(func.count(Document.id)).where(Document.folder_id == f.id)) or 0
        sub_count = await db.scalar(select(func.count(Folder.id)).where(Folder.parent_id == f.id)) or 0
        folders.append({"id": str(f.id), "name": f.name, "description": f.description, "parent_id": str(f.parent_id) if f.parent_id else None, "doc_count": doc_count, "subfolder_count": sub_count, "created_at": f.created_at.isoformat()})
    return folders

@router.post("/folders", status_code=201, dependencies=[Depends(require_permission("documents.folder.manage"))])
async def create_folder(p: FolderCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    f = Folder(project_id=p.project_id, parent_id=p.parent_id, name=p.name, description=p.description, created_by_id=current_user.id)
    db.add(f); await db.commit(); await db.refresh(f)
    return {"id": str(f.id), "name": f.name}

@router.delete("/folders/{folder_id}", status_code=204, dependencies=[Depends(require_permission("documents.folder.manage"))])
async def delete_folder(folder_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    f = await db.get(Folder, folder_id)
    if not f: raise HTTPException(404, "Folder not found")
    await log_audit(db, current_user, domain="dms", action="delete", entity_type="folder", entity_id=f.id,
                    before={"name": f.name, "project_id": str(f.project_id) if f.project_id else None})
    await db.delete(f); await db.commit()


# ── Documents ───────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    folder_id: UUID | None = None, project_id: UUID | None = None,
    status: str | None = None, tag: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Document).order_by(Document.updated_at.desc()).limit(200)
    if folder_id: q = q.where(Document.folder_id == folder_id)
    if project_id: q = q.where(Document.project_id == project_id)
    if status: q = q.where(Document.status == DocumentStatus(status))
    if tag: q = q.where(Document.tags.ilike(f"%{tag}%"))
    result = await db.execute(q)
    restricted = await _restricted_folder_ids(db) if current_user.role != UserRole.ADMIN else set()
    allowed = await _user_folder_ids(db, current_user.id) if current_user.role != UserRole.ADMIN else set()
    docs = []
    for d in result.scalars().all():
        # Docs in a restricted folder: user needs an explicit grant (or ADMIN / creator).
        if current_user.role != UserRole.ADMIN and d.folder_id and d.folder_id in restricted:
            if d.folder_id not in allowed and d.created_by_id != current_user.id:
                continue
        docs.append({"id": str(d.id), "title": d.title, "description": d.description, "tags": d.tags, "status": d.status.value, "current_version": d.current_version, "folder_id": str(d.folder_id) if d.folder_id else None, "updated_at": d.updated_at.isoformat()})
    return docs

@router.post("/documents", status_code=201, dependencies=[Depends(require_permission("documents.file.upload"))])
async def create_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    project_id: str = Form(None),
    folder_id: str = Form(None),
    description: str = Form(None),
    tags: str = Form(None),
    expiry_date: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Create document record
    doc = Document(
        project_id=UUID(project_id) if project_id and project_id != "null" else None,
        folder_id=UUID(folder_id) if folder_id and folder_id != "null" else None,
        title=title, description=description, tags=tags,
        expiry_date=datetime.fromisoformat(expiry_date) if expiry_date else None,
        created_by_id=current_user.id, current_version=1,
    )
    db.add(doc); await db.flush()

    # Save file as version 1
    file_id = str(uuid_mod.uuid4())
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{file_id}{ext}"
    content = await file.read()
    get_storage().put(stored_name, content)

    ver = DocumentVersion(
        document_id=doc.id, version_number=1, filename=stored_name,
        original_name=file.filename or "file", content_type=file.content_type,
        size_bytes=len(content), uploaded_by_id=current_user.id,
        content_text=extract_text(content, file.content_type, file.filename or ""),
    )
    db.add(ver)
    await log_audit(db, current_user, domain="dms", action="upload", entity_type="document", entity_id=doc.id,
                    after={"title": title, "size": len(content), "filename": file.filename})
    await db.commit(); await db.refresh(doc)
    return {"id": str(doc.id), "title": doc.title, "version": 1}

@router.post("/documents/{doc_id}/versions", status_code=201, dependencies=[Depends(require_permission("documents.file.upload"))])
async def upload_new_version(
    doc_id: UUID,
    file: UploadFile = File(...),
    change_notes: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")

    new_ver_num = doc.current_version + 1
    file_id = str(uuid_mod.uuid4())
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{file_id}{ext}"
    content = await file.read()
    get_storage().put(stored_name, content)

    ver = DocumentVersion(
        document_id=doc.id, version_number=new_ver_num, filename=stored_name,
        original_name=file.filename or "file", content_type=file.content_type,
        size_bytes=len(content), change_notes=change_notes, uploaded_by_id=current_user.id,
        content_text=extract_text(content, file.content_type, file.filename or ""),
    )
    db.add(ver)
    doc.current_version = new_ver_num
    await log_audit(db, current_user, domain="dms", action="version_upload", entity_type="document", entity_id=doc.id,
                    after={"version": new_ver_num, "size": len(content), "change_notes": change_notes})
    await db.commit()
    return {"id": str(doc.id), "version": new_ver_num}

@router.post("/documents/{doc_id}/versions/{version_number}/restore", dependencies=[Depends(require_permission("documents.file.upload"))])
async def restore_version(doc_id: UUID, version_number: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Promote an older version to the current one by creating a new numbered
    version whose file is a copy of the old file. History stays linear."""
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    src = (await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version_number == version_number,
        )
    )).scalar_one_or_none()
    if not src: raise HTTPException(404, f"Version {version_number} not found")

    storage = get_storage()
    src_path = storage.get_path(src.filename)
    if not src_path: raise HTTPException(404, "Source file missing on storage")

    new_ver_num = doc.current_version + 1
    file_id = str(uuid_mod.uuid4())
    ext = os.path.splitext(src.original_name or src.filename)[1]
    new_filename = f"{file_id}{ext}"
    with open(src_path, "rb") as rf:
        storage.put(new_filename, rf.read())

    ver = DocumentVersion(
        document_id=doc.id, version_number=new_ver_num, filename=new_filename,
        original_name=src.original_name, content_type=src.content_type,
        size_bytes=src.size_bytes, content_text=src.content_text,
        change_notes=f"Restored from v{version_number}",
        uploaded_by_id=current_user.id,
    )
    db.add(ver)
    doc.current_version = new_ver_num
    await log_audit(db, current_user, domain="dms", action="restore_version", entity_type="document", entity_id=doc.id,
                    before={"from_version": version_number}, after={"to_version": new_ver_num})
    await db.commit()
    return {"id": str(doc.id), "current_version": new_ver_num, "restored_from": version_number}


@router.get("/documents/{doc_id}/versions")
async def list_versions(doc_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    return [
        {"id": str(v.id), "version": v.version_number, "original_name": v.original_name, "size_bytes": v.size_bytes, "change_notes": v.change_notes, "created_at": v.created_at.isoformat()}
        for v in result.scalars().all()
    ]

@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: UUID, version: int | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    if doc.folder_id and current_user.role != UserRole.ADMIN and doc.created_by_id != current_user.id:
        folder = await db.get(Folder, doc.folder_id)
        if folder and not await _can_see_folder(db, current_user, folder):
            raise HTTPException(403, "No access to this folder")

    q = select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
    if version: q = q.where(DocumentVersion.version_number == version)
    else: q = q.order_by(DocumentVersion.version_number.desc()).limit(1)

    ver = (await db.execute(q)).scalar_one_or_none()
    if not ver: raise HTTPException(404, "Version not found")

    path = get_storage().get_path(ver.filename)
    if not path: raise HTTPException(404, "File not found on storage")
    await log_audit(db, current_user, domain="dms", action="download", entity_type="document", entity_id=doc.id,
                    after={"version": ver.version_number, "filename": ver.original_name})
    await db.commit()
    return FileResponse(path, filename=ver.original_name, media_type=ver.content_type)

@router.patch("/documents/{doc_id}")
async def update_document(doc_id: UUID, title: str | None = None, status: str | None = None, tags: str | None = None, description: str | None = None, expiry_date: str | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    before = {"title": doc.title, "status": doc.status.value, "tags": doc.tags, "description": doc.description, "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None}
    if title: doc.title = title
    if status: doc.status = DocumentStatus(status)
    if tags is not None: doc.tags = tags
    if description is not None: doc.description = description
    if expiry_date is not None: doc.expiry_date = datetime.fromisoformat(expiry_date) if expiry_date else None
    after = {"title": doc.title, "status": doc.status.value, "tags": doc.tags, "description": doc.description, "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None}
    await log_audit(db, current_user, domain="dms", action="update", entity_type="document", entity_id=doc.id, before=before, after=after)
    await db.commit()
    return {"id": str(doc.id), "title": doc.title, "status": doc.status.value}

@router.delete("/documents/{doc_id}", status_code=204, dependencies=[Depends(require_permission("documents.file.delete"))])
async def delete_document(doc_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    # Delete file versions from storage
    versions = (await db.execute(select(DocumentVersion).where(DocumentVersion.document_id == doc_id))).scalars().all()
    storage = get_storage()
    for v in versions:
        storage.delete(v.filename)
    await log_audit(db, current_user, domain="dms", action="delete", entity_type="document", entity_id=doc.id,
                    before={"title": doc.title, "versions": len(versions)})
    await db.delete(doc); await db.commit()


# ── Expiring documents ──────────────────────────────────────────────

@router.get("/documents/expiring")
async def expiring_documents(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Docs with an expiry_date within `days` days from now."""
    cutoff = datetime.utcnow() + timedelta(days=days)
    q = select(Document).where(
        Document.expiry_date.is_not(None),
        Document.expiry_date <= cutoff,
    ).order_by(Document.expiry_date)
    result = await db.execute(q)
    return [
        {"id": str(d.id), "title": d.title, "expiry_date": d.expiry_date.isoformat(),
         "status": d.status.value, "created_by_id": str(d.created_by_id) if d.created_by_id else None}
        for d in result.scalars().all()
    ]


# ── Search ──────────────────────────────────────────────────────────

@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    full_text: bool = False,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = None,
    author_id: UUID | None = None,
    file_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Search with optional filters.

    * `full_text=true` matches the extracted `content_text` on any version.
    * `date_from` / `date_to` filter by `Document.updated_at`.
    * `status` must be one of draft / review / approved / archived.
    * `author_id` filters by `created_by_id`.
    * `file_type` prefix-matches the *latest* version's content_type
      (e.g. `application/pdf` or `image/` for all images).
    """
    pattern = f"%{q}%"
    filters = [or_(Document.title.ilike(pattern), Document.tags.ilike(pattern), Document.description.ilike(pattern))]

    if full_text:
        sub = select(DocumentVersion.document_id).where(DocumentVersion.content_text.ilike(pattern)).distinct()
        filters = [or_(filters[0], Document.id.in_(sub))]

    if date_from: filters.append(Document.updated_at >= date_from)
    if date_to: filters.append(Document.updated_at <= date_to)
    if status: filters.append(Document.status == DocumentStatus(status))
    if author_id: filters.append(Document.created_by_id == author_id)
    if file_type:
        # Match on the latest version's content_type
        latest_subq = (
            select(DocumentVersion.document_id)
            .where(DocumentVersion.content_type.ilike(f"{file_type}%"))
            .distinct()
        )
        filters.append(Document.id.in_(latest_subq))

    result = await db.execute(
        select(Document).where(*filters).order_by(Document.updated_at.desc()).limit(100)
    )
    return [{"id": str(d.id), "title": d.title, "tags": d.tags, "status": d.status.value,
             "folder_id": str(d.folder_id) if d.folder_id else None,
             "updated_at": d.updated_at.isoformat()}
            for d in result.scalars().all()]


# ── DMS Dashboard ───────────────────────────────────────────────────

@router.get("/dashboard")
async def dms_dashboard(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    doc_q = select(func.count(Document.id))
    folder_q = select(func.count(Folder.id))
    ver_q = select(func.count(DocumentVersion.id))
    size_q = select(func.coalesce(func.sum(DocumentVersion.size_bytes), 0))
    if project_id:
        doc_q = doc_q.where(Document.project_id == project_id)
        folder_q = folder_q.where(Folder.project_id == project_id)

    docs = await db.scalar(doc_q) or 0
    folders = await db.scalar(folder_q) or 0
    versions = await db.scalar(ver_q) or 0
    total_size = await db.scalar(size_q) or 0

    return {
        "documents": docs, "folders": folders, "versions": versions,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
    }


# ── E-Signature ─────────────────────────────────────────────────────

class SignatureRequestCreate(BaseModel):
    document_id: UUID; signer_email: str; signer_name: str | None = None; message: str | None = None

class SignaturePayload(BaseModel):
    signature_data: str

@router.get("/signatures")
async def list_signatures(document_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(SignatureRequest).order_by(SignatureRequest.created_at.desc()).limit(100)
    if document_id: q = q.where(SignatureRequest.document_id == document_id)
    result = await db.execute(q)
    return [{"id": str(s.id), "document_id": str(s.document_id), "signer_email": s.signer_email, "signer_name": s.signer_name, "status": s.status.value, "signed_at": s.signed_at.isoformat() if s.signed_at else None, "token": s.token} for s in result.scalars().all()]

@router.post("/signatures", status_code=201, dependencies=[Depends(require_permission("documents.signature.manage"))])
async def request_signature(p: SignatureRequestCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sig = SignatureRequest(document_id=p.document_id, signer_email=p.signer_email, signer_name=p.signer_name,
                           message=p.message, token=secrets.token_urlsafe(32), requested_by_id=current_user.id)
    db.add(sig)
    await log_audit(db, current_user, domain="dms", action="signature_requested", entity_type="document", entity_id=p.document_id,
                    after={"signer_email": p.signer_email})
    await db.commit(); await db.refresh(sig)

    # Fire email to signer
    doc = await db.get(Document, p.document_id)
    if doc:
        from app.services.email import queue_signature_request
        queue_signature_request(p.signer_email, doc.title, sig.token, p.message)
    return {"id": str(sig.id), "token": sig.token}

@router.post("/signatures/{token}/sign")
async def sign_document(token: str, p: SignaturePayload, db: AsyncSession = Depends(get_db)):
    sig = (await db.execute(select(SignatureRequest).where(SignatureRequest.token == token))).scalar_one_or_none()
    if not sig: raise HTTPException(404, "Signature request not found")
    if sig.status != SignatureRequestStatus.PENDING: raise HTTPException(400, f"Request is {sig.status.value}")
    sig.status = SignatureRequestStatus.SIGNED
    sig.signature_data = p.signature_data
    sig.signed_at = datetime.utcnow()
    await db.commit()
    return {"id": str(sig.id), "status": sig.status.value}

@router.post("/signatures/{sig_id}/decline")
async def decline_signature(sig_id: UUID, db: AsyncSession = Depends(get_db)):
    sig = await db.get(SignatureRequest, sig_id)
    if not sig: raise HTTPException(404, "Not found")
    sig.status = SignatureRequestStatus.DECLINED
    await db.commit()
    return {"id": str(sig.id), "status": sig.status.value}


# ── Templates ───────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str; category: str | None = None; description: str | None = None
    body: str; variables: str | None = None

class TemplateInstantiate(BaseModel):
    folder_id: UUID | None = None; project_id: UUID | None = None
    title: str; vars: dict[str, str] = {}

@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentTemplate).order_by(DocumentTemplate.name))
    return [{"id": str(t.id), "name": t.name, "category": t.category, "description": t.description, "variables": t.variables} for t in result.scalars().all()]

@router.post("/templates", status_code=201)
async def create_template(p: TemplateCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = DocumentTemplate(name=p.name, category=p.category, description=p.description, body=p.body, variables=p.variables, created_by_id=current_user.id)
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id": str(t.id), "name": t.name}

@router.post("/templates/{template_id}/instantiate", status_code=201)
async def instantiate_template(template_id: UUID, p: TemplateInstantiate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = await db.get(DocumentTemplate, template_id)
    if not t: raise HTTPException(404, "Template not found")
    body = t.body
    for k, v in (p.vars or {}).items():
        body = body.replace(f"{{{{{k}}}}}", str(v))
    # Write rendered file as .txt
    file_id = str(uuid_mod.uuid4())
    stored_name = f"{file_id}.txt"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    doc = Document(project_id=p.project_id, folder_id=p.folder_id, title=p.title,
                   description=f"From template: {t.name}", created_by_id=current_user.id, current_version=1)
    db.add(doc); await db.flush()
    ver = DocumentVersion(document_id=doc.id, version_number=1, filename=stored_name,
                          original_name=f"{p.title}.txt", content_type="text/plain",
                          size_bytes=len(body.encode("utf-8")), content_text=body, uploaded_by_id=current_user.id)
    db.add(ver); await db.commit()
    return {"id": str(doc.id), "title": doc.title}


# ── Folder Permissions (ACL) ────────────────────────────────────────

class FolderPermissionCreate(BaseModel):
    folder_id: UUID; user_id: UUID; permission: str = "read"

@router.get("/folders/{folder_id}/permissions")
async def list_folder_permissions(folder_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FolderPermission).where(FolderPermission.folder_id == folder_id))
    return [{"id": str(p.id), "folder_id": str(p.folder_id), "user_id": str(p.user_id), "permission": p.permission} for p in result.scalars().all()]

@router.post("/folders/permissions", status_code=201)
async def grant_folder_permission(p: FolderPermissionCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(FolderPermission).where(FolderPermission.folder_id == p.folder_id, FolderPermission.user_id == p.user_id))).scalar_one_or_none()
    if existing:
        existing.permission = p.permission
        await db.commit()
        return {"id": str(existing.id), "permission": existing.permission}
    fp = FolderPermission(folder_id=p.folder_id, user_id=p.user_id, permission=p.permission)
    db.add(fp); await db.commit(); await db.refresh(fp)
    return {"id": str(fp.id), "permission": fp.permission}

@router.delete("/folders/permissions/{perm_id}", status_code=204)
async def revoke_folder_permission(perm_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await db.get(FolderPermission, perm_id)
    if not p: raise HTTPException(404, "Not found")
    await db.delete(p); await db.commit()


# ── Retention Policies ──────────────────────────────────────────────

class RetentionPolicyCreate(BaseModel):
    name: str; folder_id: UUID | None = None; tag_match: str | None = None
    days_after: int; action: RetentionAction = RetentionAction.ARCHIVE

@router.get("/retention-policies")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RetentionPolicy).order_by(RetentionPolicy.name))
    return [{"id": str(r.id), "name": r.name, "folder_id": str(r.folder_id) if r.folder_id else None, "tag_match": r.tag_match, "days_after": r.days_after, "action": r.action.value, "is_active": r.is_active} for r in result.scalars().all()]

@router.post("/retention-policies", status_code=201, dependencies=[Depends(require_permission("documents.retention.manage"))])
async def create_policy(p: RetentionPolicyCreate, db: AsyncSession = Depends(get_db)):
    r = RetentionPolicy(**p.model_dump())
    db.add(r); await db.commit(); await db.refresh(r)
    return {"id": str(r.id)}

@router.post("/retention-policies/apply", dependencies=[Depends(require_permission("documents.retention.manage"))])
async def apply_retention(db: AsyncSession = Depends(get_db)):
    policies = (await db.execute(select(RetentionPolicy).where(RetentionPolicy.is_active == True))).scalars().all()
    archived = deleted = 0
    now = datetime.utcnow()
    for pol in policies:
        cutoff = now - timedelta(days=pol.days_after)
        q = select(Document).where(Document.updated_at < cutoff)
        if pol.folder_id: q = q.where(Document.folder_id == pol.folder_id)
        if pol.tag_match: q = q.where(Document.tags.ilike(f"%{pol.tag_match}%"))
        docs = (await db.execute(q)).scalars().all()
        for d in docs:
            if pol.action == RetentionAction.ARCHIVE and d.status != DocumentStatus.ARCHIVED:
                d.status = DocumentStatus.ARCHIVED
                archived += 1
            elif pol.action == RetentionAction.DELETE:
                versions = (await db.execute(select(DocumentVersion).where(DocumentVersion.document_id == d.id))).scalars().all()
                for v in versions:
                    path = os.path.join(UPLOAD_DIR, v.filename)
                    if os.path.exists(path): os.remove(path)
                await db.delete(d)
                deleted += 1
    await db.commit()
    return {"archived": archived, "deleted": deleted}


# ── Entity Links ────────────────────────────────────────────────────

class EntityLinkCreate(BaseModel):
    document_id: UUID; entity_type: EntityType; entity_id: UUID

@router.get("/entity-links")
async def list_entity_links(entity_type: EntityType | None = None, entity_id: UUID | None = None, document_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(EntityLink).order_by(EntityLink.created_at.desc()).limit(200)
    if entity_type: q = q.where(EntityLink.entity_type == entity_type)
    if entity_id: q = q.where(EntityLink.entity_id == entity_id)
    if document_id: q = q.where(EntityLink.document_id == document_id)
    result = await db.execute(q)
    links = []
    for l in result.scalars().all():
        d = await db.get(Document, l.document_id)
        links.append({"id": str(l.id), "document_id": str(l.document_id), "document_title": d.title if d else None, "entity_type": l.entity_type.value, "entity_id": str(l.entity_id)})
    return links

@router.post("/entity-links", status_code=201)
async def create_entity_link(p: EntityLinkCreate, db: AsyncSession = Depends(get_db)):
    l = EntityLink(document_id=p.document_id, entity_type=p.entity_type, entity_id=p.entity_id)
    db.add(l); await db.commit(); await db.refresh(l)
    return {"id": str(l.id)}

@router.delete("/entity-links/{link_id}", status_code=204)
async def delete_entity_link(link_id: UUID, db: AsyncSession = Depends(get_db)):
    l = await db.get(EntityLink, link_id)
    if not l: raise HTTPException(404, "Not found")
    await db.delete(l); await db.commit()


# ── Preview (inline media_type for browser view) ───────────────────

@router.get("/documents/{doc_id}/preview")
async def preview_document(doc_id: UUID, version: int | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    if doc.folder_id and current_user.role != UserRole.ADMIN and doc.created_by_id != current_user.id:
        folder = await db.get(Folder, doc.folder_id)
        if folder and not await _can_see_folder(db, current_user, folder):
            raise HTTPException(403, "No access to this folder")
    q = select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
    if version: q = q.where(DocumentVersion.version_number == version)
    else: q = q.order_by(DocumentVersion.version_number.desc()).limit(1)
    ver = (await db.execute(q)).scalar_one_or_none()
    if not ver: raise HTTPException(404, "Version not found")
    path = get_storage().get_path(ver.filename)
    if not path: raise HTTPException(404, "File not found on storage")
    await log_audit(db, current_user, domain="dms", action="view", entity_type="document", entity_id=doc.id,
                    after={"version": ver.version_number})
    await db.commit()
    return FileResponse(path, media_type=ver.content_type or "application/octet-stream")


# ── Check-in / Check-out Locks ──────────────────────────────────────

class CheckoutPayload(BaseModel):
    note: str | None = None

@router.post("/documents/{doc_id}/checkout")
async def checkout_doc(doc_id: UUID, p: CheckoutPayload, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.get(DocumentLock, doc_id)
    if existing and existing.user_id != current_user.id:
        raise HTTPException(409, f"Locked by another user since {existing.locked_at.isoformat()[:19]}")
    if existing:
        existing.note = p.note
    else:
        db.add(DocumentLock(document_id=doc_id, user_id=current_user.id, note=p.note))
    await db.commit()
    return {"document_id": str(doc_id), "locked_by": str(current_user.id)}

@router.post("/documents/{doc_id}/checkin")
async def checkin_doc(doc_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    lock = await db.get(DocumentLock, doc_id)
    if not lock: return {"document_id": str(doc_id), "was_locked": False}
    if lock.user_id != current_user.id:
        raise HTTPException(403, "You don't hold this lock")
    await db.delete(lock); await db.commit()
    return {"document_id": str(doc_id), "unlocked": True}

@router.get("/locks")
async def list_locks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentLock))
    out = []
    for l in result.scalars().all():
        d = await db.get(Document, l.document_id)
        out.append({"document_id": str(l.document_id), "title": d.title if d else None,
                    "user_id": str(l.user_id), "locked_at": l.locked_at.isoformat() if l.locked_at else None,
                    "note": l.note})
    return out


# ── Version Diff ────────────────────────────────────────────────────

@router.get("/documents/{doc_id}/diff")
async def diff_versions(doc_id: UUID, v1: int, v2: int, db: AsyncSession = Depends(get_db)):
    import difflib
    versions = (await db.execute(select(DocumentVersion).where(DocumentVersion.document_id == doc_id, DocumentVersion.version_number.in_([v1, v2])))).scalars().all()
    by_num = {v.version_number: v for v in versions}
    a = by_num.get(v1); b = by_num.get(v2)
    if not a or not b: raise HTTPException(404, "One or both versions not found")
    if not a.content_text or not b.content_text:
        return {"v1": v1, "v2": v2, "message": "Text extraction not available for one or both versions", "diff": []}
    diff = list(difflib.unified_diff(
        (a.content_text or "").splitlines(), (b.content_text or "").splitlines(),
        fromfile=f"v{v1}", tofile=f"v{v2}", lineterm="", n=2))
    return {"v1": v1, "v2": v2, "diff": diff[:1000]}


# ── Workflows ───────────────────────────────────────────────────────

class WorkflowStepIn(BaseModel):
    step_order: int; role: str; assignee_id: UUID | None = None

class WorkflowCreate(BaseModel):
    document_id: UUID; name: str; steps: list[WorkflowStepIn]

@router.get("/workflows")
async def list_workflows(document_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(DocumentWorkflow).order_by(DocumentWorkflow.created_at.desc()).limit(100)
    if document_id: q = q.where(DocumentWorkflow.document_id == document_id)
    result = await db.execute(q)
    out = []
    for w in result.scalars().all():
        steps = (await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == w.id).order_by(WorkflowStep.step_order))).scalars().all()
        out.append({"id": str(w.id), "document_id": str(w.document_id), "name": w.name,
                    "current_step": w.current_step, "is_complete": w.is_complete,
                    "steps": [{"id": str(s.id), "step_order": s.step_order, "role": s.role,
                               "assignee_id": str(s.assignee_id) if s.assignee_id else None,
                               "status": s.status.value, "note": s.note} for s in steps]})
    return out

@router.post("/workflows", status_code=201, dependencies=[Depends(require_permission("documents.workflow.manage"))])
async def create_workflow(p: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    if not p.steps: raise HTTPException(400, "At least one step required")
    w = DocumentWorkflow(document_id=p.document_id, name=p.name)
    db.add(w); await db.flush()
    for s in sorted(p.steps, key=lambda x: x.step_order):
        db.add(WorkflowStep(workflow_id=w.id, step_order=s.step_order, role=s.role, assignee_id=s.assignee_id))
    await db.commit(); await db.refresh(w)
    return {"id": str(w.id)}

class WorkflowAdvance(BaseModel):
    decision: str  # approved | rejected
    note: str | None = None

@router.post("/workflows/{wf_id}/advance", dependencies=[Depends(require_permission("documents.workflow.manage"))])
async def advance_workflow(wf_id: UUID, p: WorkflowAdvance, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    w = await db.get(DocumentWorkflow, wf_id)
    if not w or w.is_complete: raise HTTPException(400, "Workflow not active")
    steps = (await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == wf_id).order_by(WorkflowStep.step_order))).scalars().all()
    if w.current_step >= len(steps): raise HTTPException(400, "No pending step")
    step = steps[w.current_step]
    step.status = WorkflowStepStatus(p.decision)
    step.note = p.note
    step.decided_at = datetime.utcnow()
    if p.decision == "rejected":
        w.is_complete = True
        d = await db.get(Document, w.document_id)
        if d: d.status = DocumentStatus.DRAFT
    else:
        w.current_step += 1
        if w.current_step >= len(steps):
            w.is_complete = True
            d = await db.get(Document, w.document_id)
            if d: d.status = DocumentStatus.APPROVED
    await log_audit(db, current_user, domain="dms", action="workflow_advance", entity_type="document", entity_id=w.document_id,
                    after={"workflow_id": str(w.id), "decision": p.decision, "step": w.current_step, "complete": w.is_complete})
    await db.commit()
    return {"id": str(w.id), "current_step": w.current_step, "is_complete": w.is_complete}


# ── Annotations ─────────────────────────────────────────────────────

class AnnotationCreate(BaseModel):
    document_id: UUID; version_number: int | None = None; page: int | None = None
    anchor_text: str | None = None; body: str

@router.get("/annotations")
async def list_annotations(document_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentAnnotation).where(DocumentAnnotation.document_id == document_id).order_by(DocumentAnnotation.created_at))
    return [{"id": str(a.id), "version_number": a.version_number, "page": a.page, "anchor_text": a.anchor_text,
             "body": a.body, "author_id": str(a.author_id) if a.author_id else None,
             "resolved": a.resolved, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in result.scalars().all()]

@router.post("/annotations", status_code=201)
async def create_annotation(p: AnnotationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = DocumentAnnotation(document_id=p.document_id, version_number=p.version_number, page=p.page,
                           anchor_text=p.anchor_text, body=p.body, author_id=current_user.id)
    db.add(a); await db.commit(); await db.refresh(a)
    return {"id": str(a.id)}

@router.post("/annotations/{ann_id}/resolve")
async def resolve_annotation(ann_id: UUID, db: AsyncSession = Depends(get_db)):
    a = await db.get(DocumentAnnotation, ann_id)
    if not a: raise HTTPException(404, "Not found")
    a.resolved = True; await db.commit()
    return {"id": str(a.id), "resolved": True}


# ── E-Sign Providers ────────────────────────────────────────────────

class ESignProviderCreate(BaseModel):
    name: str; provider_type: ESignProviderType = ESignProviderType.INTERNAL
    api_base_url: str | None = None; api_key: str | None = None
    webhook_secret: str | None = None; is_default: bool = False

@router.get("/esign-providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ESignProvider).order_by(ESignProvider.name))
    return [{"id": str(p.id), "name": p.name, "provider_type": p.provider_type.value,
             "api_base_url": p.api_base_url, "is_default": p.is_default, "is_active": p.is_active}
            for p in result.scalars().all()]

@router.post("/esign-providers", status_code=201)
async def create_provider(p: ESignProviderCreate, db: AsyncSession = Depends(get_db)):
    masked = f"****{p.api_key[-4:]}" if p.api_key and len(p.api_key) >= 4 else None
    if p.is_default:
        # Unset other defaults
        others = (await db.execute(select(ESignProvider).where(ESignProvider.is_default == True))).scalars().all()
        for o in others: o.is_default = False
    prov = ESignProvider(name=p.name, provider_type=p.provider_type, api_base_url=p.api_base_url,
                         api_key_masked=masked, webhook_secret=p.webhook_secret, is_default=p.is_default)
    db.add(prov); await db.commit(); await db.refresh(prov)
    return {"id": str(prov.id), "name": prov.name}


class ESignWebhookPayload(BaseModel):
    external_request_id: str; event: str
    signer_email: str | None = None; signed_at: str | None = None

@router.post("/esign-webhooks/{provider_id}")
async def esign_webhook(provider_id: UUID, p: ESignWebhookPayload, db: AsyncSession = Depends(get_db)):
    """Unified webhook entrypoint for any provider. Match by signer_email + pending request."""
    prov = await db.get(ESignProvider, provider_id)
    if not prov: raise HTTPException(404, "Provider not found")
    if p.event in ("signed", "completed") and p.signer_email:
        req = (await db.execute(select(SignatureRequest).where(
            SignatureRequest.signer_email == p.signer_email,
            SignatureRequest.status == SignatureRequestStatus.PENDING,
        ).order_by(SignatureRequest.created_at.desc()).limit(1))).scalar_one_or_none()
        if req:
            req.status = SignatureRequestStatus.SIGNED
            req.signed_at = datetime.fromisoformat(p.signed_at) if p.signed_at else datetime.utcnow()
            await db.commit()
            return {"matched": str(req.id), "status": "signed"}
    return {"received": True, "event": p.event}


# ── Virus Scan Hook ─────────────────────────────────────────────────

def _stub_scan(content: bytes) -> tuple[ScanStatus, str | None]:
    """Stub scanner. Flags files containing a synthetic test marker as infected.

    Use `PMPROJECT-SCAN-TEST-INFECTED` in file content to simulate detection.
    (Avoids the real EICAR string so the test isn't quarantined by host AV.)
    """
    if b"PMPROJECT-SCAN-TEST-INFECTED" in content:
        return ScanStatus.INFECTED, "Synthetic test marker"
    return ScanStatus.CLEAN, None

@router.post("/versions/{version_id}/scan")
async def scan_version(version_id: UUID, db: AsyncSession = Depends(get_db)):
    ver = await db.get(DocumentVersion, version_id)
    if not ver: raise HTTPException(404, "Version not found")
    path = os.path.join(UPLOAD_DIR, ver.filename)
    if not os.path.exists(path): raise HTTPException(404, "File not on disk")
    with open(path, "rb") as f:
        content = f.read()
    status, details = _stub_scan(content)
    sr = ScanResult(version_id=version_id, status=status, details=details)
    db.add(sr); await db.commit()
    return {"version_id": str(version_id), "status": status.value, "details": details}

@router.get("/scan-results")
async def list_scan_results(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ScanResult).order_by(ScanResult.scanned_at.desc()).limit(200)
    if status: q = q.where(ScanResult.status == ScanStatus(status))
    result = await db.execute(q)
    return [{"id": str(r.id), "version_id": str(r.version_id), "status": r.status.value, "details": r.details,
             "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None}
            for r in result.scalars().all()]


# ── Shareable public links ──────────────────────────────────────────

class ShareLinkCreate(BaseModel):
    expires_in_days: int | None = 7  # None = no expiry


@router.post("/documents/{doc_id}/share", status_code=201)
async def create_share_link(doc_id: UUID, p: ShareLinkCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    token = secrets.token_urlsafe(32)
    expires_at = None
    if p.expires_in_days and p.expires_in_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=p.expires_in_days)
    link = DocumentShareLink(document_id=doc_id, token=token, expires_at=expires_at, created_by_id=current_user.id)
    db.add(link)
    await log_audit(db, current_user, domain="dms", action="share_link_created", entity_type="document", entity_id=doc.id,
                    after={"expires_at": expires_at.isoformat() if expires_at else None})
    await db.commit(); await db.refresh(link)
    return {"id": str(link.id), "token": token, "expires_at": expires_at.isoformat() if expires_at else None}


@router.get("/documents/{doc_id}/share")
async def list_share_links(doc_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(DocumentShareLink).where(DocumentShareLink.document_id == doc_id))).all()
    return [{"id": str(r.id), "token": r.token, "expires_at": r.expires_at.isoformat() if r.expires_at else None,
             "download_count": r.download_count, "is_revoked": r.is_revoked, "created_at": r.created_at.isoformat()}
            for r in rows]


@router.delete("/share/{link_id}", status_code=204)
async def revoke_share_link(link_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    link = await db.get(DocumentShareLink, link_id)
    if not link: raise HTTPException(404, "Share link not found")
    link.is_revoked = True
    await log_audit(db, current_user, domain="dms", action="share_link_revoked", entity_type="document", entity_id=link.document_id)
    await db.commit()



# ── Reports ─────────────────────────────────────────────────────────

@router.get("/reports/usage")
async def report_usage(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    """Top downloaders and most-accessed documents over the given window,
    sourced from the global audit log."""
    from app.models.cross import AuditEntry
    since = datetime.utcnow() - timedelta(days=days)
    base = select(AuditEntry).where(
        AuditEntry.domain == "dms",
        AuditEntry.action.in_(["download", "view"]),
        AuditEntry.created_at >= since,
    )

    # Top downloaders
    by_user = (await db.execute(
        select(AuditEntry.user_id, func.count(AuditEntry.id).label("n"))
        .where(AuditEntry.domain == "dms", AuditEntry.action.in_(["download", "view"]), AuditEntry.created_at >= since)
        .group_by(AuditEntry.user_id).order_by(func.count(AuditEntry.id).desc()).limit(10)
    )).all()

    # Most-accessed documents
    by_doc = (await db.execute(
        select(AuditEntry.entity_id, func.count(AuditEntry.id).label("n"))
        .where(AuditEntry.domain == "dms", AuditEntry.action.in_(["download", "view"]), AuditEntry.created_at >= since)
        .group_by(AuditEntry.entity_id).order_by(func.count(AuditEntry.id).desc()).limit(10)
    )).all()

    # Resolve doc titles for readability
    doc_ids = [row[0] for row in by_doc if row[0]]
    titles: dict[str, str] = {}
    if doc_ids:
        docs = await db.scalars(select(Document).where(Document.id.in_([UUID(d) for d in doc_ids])))
        titles = {str(d.id): d.title for d in docs.all()}

    return {
        "window_days": days,
        "top_users": [{"user_id": str(u) if u else None, "actions": n} for u, n in by_user],
        "top_documents": [{"document_id": d, "title": titles.get(d), "actions": n} for d, n in by_doc],
    }


@router.get("/reports/audit")
async def report_audit(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    action: str | None = None,
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Flat DMS audit entries for compliance exports."""
    from app.models.cross import AuditEntry
    q = select(AuditEntry).where(AuditEntry.domain == "dms")
    if date_from: q = q.where(AuditEntry.created_at >= date_from)
    if date_to: q = q.where(AuditEntry.created_at <= date_to)
    if action: q = q.where(AuditEntry.action == action)
    q = q.order_by(AuditEntry.created_at.desc()).limit(limit)
    rows = (await db.scalars(q)).all()
    return [{"id": str(e.id), "user_id": str(e.user_id) if e.user_id else None, "action": e.action,
             "entity_type": e.entity_type, "entity_id": e.entity_id,
             "created_at": e.created_at.isoformat(),
             "before": e.before_data, "after": e.after_data}
            for e in rows]


@router.get("/reports/pending-approvals")
async def report_pending_approvals(db: AsyncSession = Depends(get_db)):
    """Workflows and signature requests awaiting action."""
    wfs = (await db.scalars(select(DocumentWorkflow).where(DocumentWorkflow.is_complete == False))).all()  # noqa: E712
    sigs = (await db.scalars(select(SignatureRequest).where(SignatureRequest.status == SignatureRequestStatus.PENDING))).all()
    return {
        "workflows": [{"id": str(w.id), "name": w.name, "document_id": str(w.document_id),
                       "current_step": w.current_step, "created_at": w.created_at.isoformat()}
                      for w in wfs],
        "signatures": [{"id": str(s.id), "document_id": str(s.document_id), "signer_email": s.signer_email,
                        "created_at": s.created_at.isoformat()}
                       for s in sigs],
    }

