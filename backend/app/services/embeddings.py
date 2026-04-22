"""Text embeddings (#49) — used by semantic search + doc Q&A.

When `LLM_API_KEY` is set, calls the OpenAI-compatible `/embeddings` endpoint
with `text-embedding-3-small` (or whatever `LLM_EMBEDDING_MODEL` is). When
unset, falls back to a deterministic local "embedding" — a hashed token-frequency
vector that's *meaningless for similarity but stable* — so the search
infrastructure stays demoable without API credits.

Text chunking: simple ~500-character splitter with 80-char overlap. Real
production setups would use a sentence-aware splitter (LangChain etc.) but
keeping this lean.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Iterable

import httpx

from app.config import settings
from app.models.dms import EMBEDDING_DIM

logger = logging.getLogger(__name__)


CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
EMBEDDING_MODEL = "text-embedding-3-small"


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split into overlapping windows. Splits on whitespace where possible to
    avoid mid-word breaks; gives up and hard-cuts if a chunk is one giant word."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            out.append(text[start:].strip())
            break
        # Backtrack to whitespace if possible (within last 80 chars)
        cut = text.rfind(" ", start + int(size * 0.6), end)
        if cut == -1:
            cut = end
        out.append(text[start:cut].strip())
        start = max(cut - overlap, start + 1)
    return [c for c in out if c]


def _is_real_configured() -> bool:
    return bool(settings.llm_api_key)


def _mock_embed(text: str) -> list[float]:
    """Token-frequency hashed vector. Tokens hash to dimensions modulo
    EMBEDDING_DIM, contributing 1.0 each. Then L2-normalise. Deterministic.
    Lets cosine similarity work between texts that share tokens."""
    vec = [0.0] * EMBEDDING_DIM
    for tok in re.findall(r"[a-zA-Z]{2,}", text.lower()):
        h = int(hashlib.sha256(tok.encode()).hexdigest()[:8], 16)
        vec[h % EMBEDDING_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch. Uses real API if configured, else deterministic mock.
    Always returns one vector per input text in order."""
    if not texts:
        return []
    if not _is_real_configured():
        return [_mock_embed(t) for t in texts]
    try:
        url = settings.llm_base_url.rstrip("/") + "/embeddings"
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                url,
                json={"model": EMBEDDING_MODEL, "input": texts},
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            r.raise_for_status()
            data = r.json()
        return [item["embedding"] for item in data.get("data", [])]
    except Exception:
        logger.warning("Embedding API call failed, falling back to mock", exc_info=True)
        return [_mock_embed(t) for t in texts]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    a = list(a); b = list(b)
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)
