"""Semantic search + doc Q&A (#49).

  * POST /api/dms/embeddings/rebuild?document_id= — embed (or re-embed) one
    document, or all documents if no id given. Idempotent: deletes existing
    chunks for the doc before inserting new ones.
  * GET  /api/dms/search?semantic=true&q= — pgvector cosine search across
    chunks; returns top-K hits with the source document.
  * POST /api/dms/qa  {q} — runs the same retrieval, then either streams the
    answer through the LLM (when configured) or returns the top chunks raw.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.dms import Document, DocumentChunk, DocumentVersion, HAS_PGVECTOR
from app.services.embeddings import chunk_text, embed_texts

router = APIRouter(prefix="/api/dms", tags=["dms-semantic"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


# ── Embedding rebuild ───────────────────────────────────────────────


async def _read_text_for_version(db: AsyncSession, version: DocumentVersion) -> str:
    """Best-effort text extraction from a stored version. The DMS has OCR
    integration (#29); we try the stored OCR text first if available, then
    fall back to the file path's filename + any inline notes. Real production
    setups would call out to Tesseract / Apache Tika here for PDFs/Office docs."""
    text_parts: list[str] = []
    if getattr(version, "extracted_text", None):
        text_parts.append(version.extracted_text)
    # Fall back to filename + version notes so at least *some* text exists for the mock embed
    if version.file_name:
        text_parts.append(version.file_name)
    if getattr(version, "notes", None):
        text_parts.append(version.notes)
    return "\n".join(text_parts).strip()


@router.post("/embeddings/rebuild", dependencies=[Depends(require_permission("documents.file.upload"))])
async def rebuild_embeddings(
    document_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not HAS_PGVECTOR:
        raise HTTPException(503, "pgvector extension not available — install postgres image with pgvector and restart")
    docs_q = select(Document)
    if document_id:
        docs_q = docs_q.where(Document.id == document_id)
    docs = (await db.execute(docs_q)).scalars().all()
    if document_id and not docs:
        raise HTTPException(404, "Document not found")

    total_chunks = 0
    embedded_docs = 0
    for doc in docs:
        # Latest version
        ver_q = await db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number.desc()).limit(1)
        )
        ver = ver_q.scalar_one_or_none()
        if not ver:
            continue
        body = await _read_text_for_version(db, ver)
        if not body:
            continue
        # Wipe existing chunks for this doc
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        chunks = chunk_text(body)
        if not chunks:
            continue
        embeddings = embed_texts(chunks)
        for i, (content, vec) in enumerate(zip(chunks, embeddings)):
            db.add(DocumentChunk(
                document_id=doc.id,
                document_version_id=ver.id,
                chunk_index=i,
                content=content,
                embedding=vec,
            ))
        total_chunks += len(chunks)
        embedded_docs += 1
    await db.commit()
    return {
        "documents_embedded": embedded_docs,
        "documents_total": len(docs),
        "chunks_written": total_chunks,
        "embedding_source": "llm" if settings.llm_api_key else "mock",
    }


# ── Semantic search ─────────────────────────────────────────────────


@router.get("/search/semantic")
async def semantic_search(
    q: str = Query(..., min_length=2),
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if not HAS_PGVECTOR:
        raise HTTPException(503, "pgvector extension not available")
    q_vec = embed_texts([q])[0]
    # pgvector's `<=>` operator = cosine distance (smaller = more similar)
    sql = text("""
        SELECT c.id, c.document_id, c.chunk_index, c.content,
               d.title AS doc_title, d.id AS doc_id,
               1 - (c.embedding <=> CAST(:q AS vector)) AS score
        FROM dms_document_chunks c
        JOIN dms_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> CAST(:q AS vector)
        LIMIT :k
    """)
    rows = (await db.execute(sql, {"q": str(q_vec), "k": top_k})).mappings().all()
    return [
        {
            "chunk_id": str(r["id"]),
            "document_id": str(r["doc_id"]),
            "document_title": r["doc_title"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "score": float(r["score"] or 0),
        }
        for r in rows
    ]


# ── Document Q&A ────────────────────────────────────────────────────


class QaRequest(BaseModel):
    question: str
    top_k: int = 5


@router.post("/qa")
async def doc_qa(p: QaRequest, db: AsyncSession = Depends(get_db)):
    if not HAS_PGVECTOR:
        raise HTTPException(503, "pgvector extension not available")
    q = p.question.strip()
    if not q:
        raise HTTPException(400, "Empty question")
    q_vec = embed_texts([q])[0]
    sql = text("""
        SELECT c.id, c.content, d.title AS doc_title, d.id AS doc_id,
               1 - (c.embedding <=> CAST(:q AS vector)) AS score
        FROM dms_document_chunks c
        JOIN dms_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> CAST(:q AS vector)
        LIMIT :k
    """)
    rows = (await db.execute(sql, {"q": str(q_vec), "k": p.top_k})).mappings().all()
    chunks = [
        {
            "chunk_id": str(r["id"]),
            "document_id": str(r["doc_id"]),
            "document_title": r["doc_title"],
            "content": r["content"],
            "score": float(r["score"] or 0),
        }
        for r in rows
    ]
    if not chunks:
        return {"answer": None, "sources": [], "note": "No documents indexed yet — POST /api/dms/embeddings/rebuild first."}

    answer: str | None = None
    answer_source = "mock"
    if settings.llm_api_key:
        try:
            answer, answer_source = await _llm_answer(q, chunks)
        except Exception:
            logger.warning("LLM answer call failed", exc_info=True)
            answer_source = "mock_after_llm_failure"
    if answer is None:
        # Without LLM, just stitch the top chunks into a brief evidence-based response.
        answer = (
            f"Based on the documents indexed, the most relevant passages for \"{q}\" are:\n\n"
            + "\n\n".join(f"— {c['document_title']}: {c['content']}" for c in chunks[:3])
        )
    return {"answer": answer, "sources": chunks, "answer_source": answer_source}


async def _llm_answer(question: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
    import httpx
    context = "\n\n".join(
        f"[Source {i+1}: {c['document_title']}]\n{c['content']}"
        for i, c in enumerate(chunks)
    )
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise document Q&A assistant. Answer the user's question using ONLY the "
                    "passages provided. Cite sources inline as [Source N]. If the passages don't "
                    "contain the answer, say so plainly."
                ),
            },
            {"role": "user", "content": f"PASSAGES:\n{context}\n\nQUESTION: {question}"},
        ],
        "temperature": 0.2,
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        r.raise_for_status()
        data = r.json()
    msg = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
    return msg, "llm"
