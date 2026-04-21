"""Pluggable file storage backend.

Select implementation via env:
    DMS_STORAGE=local   (default; writes to /app/uploads/dms)
    DMS_STORAGE=s3      (requires boto3 + AWS-style env vars)

S3 env vars when DMS_STORAGE=s3:
    S3_BUCKET            bucket name (required)
    S3_ENDPOINT_URL      optional — set for MinIO / R2 / custom endpoints
    S3_REGION            AWS region (default: us-east-1)
    AWS_ACCESS_KEY_ID    or use instance role / env defaults
    AWS_SECRET_ACCESS_KEY

The interface is deliberately minimal: put/get_path/delete. Callers keep
working with on-disk file paths for FileResponse streaming — S3 downloads
to a tempfile on access. Good enough for moderate volume; stream-on-demand
is a future optimization.
"""

from __future__ import annotations

import logging
import os
import tempfile
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def get_path(self, key: str) -> str | None:
        """Return a filesystem path to a file with this key's contents.
        For local storage this is the permanent path; for remote storage
        it's a temp file the caller should treat as ephemeral."""

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorage(StorageBackend):
    def __init__(self, root: str):
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def _full(self, key: str) -> str:
        return os.path.join(self.root, key)

    def put(self, key: str, data: bytes) -> None:
        with open(self._full(key), "wb") as f:
            f.write(data)

    def get_path(self, key: str) -> str | None:
        p = self._full(key)
        return p if os.path.exists(p) else None

    def delete(self, key: str) -> None:
        p = self._full(key)
        if os.path.exists(p):
            os.remove(p)

    def exists(self, key: str) -> bool:
        return os.path.exists(self._full(key))


class S3Storage(StorageBackend):
    """S3-compatible backend (AWS S3, MinIO, Cloudflare R2, etc.)."""

    def __init__(self):
        import boto3  # type: ignore
        self.bucket = os.environ["S3_BUCKET"]
        kwargs = {"region_name": os.environ.get("S3_REGION", "us-east-1")}
        if endpoint := os.environ.get("S3_ENDPOINT_URL"):
            kwargs["endpoint_url"] = endpoint
        self.client = boto3.client("s3", **kwargs)

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get_path(self, key: str) -> str | None:
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            self.client.download_fileobj(self.bucket, key, tmp)
            tmp.close()
            return tmp.name
        except Exception:
            logger.warning("S3 fetch failed for %s", key, exc_info=True)
            return None

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            logger.warning("S3 delete failed for %s", key, exc_info=True)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


# ── Module-level singleton ──────────────────────────────────────────

_backend: StorageBackend | None = None

DEFAULT_LOCAL_ROOT = "/app/uploads/dms"


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        kind = os.environ.get("DMS_STORAGE", "local").lower()
        if kind == "s3":
            _backend = S3Storage()
            logger.info("DMS storage: S3 bucket=%s", os.environ.get("S3_BUCKET"))
        else:
            _backend = LocalStorage(os.environ.get("DMS_LOCAL_ROOT", DEFAULT_LOCAL_ROOT))
            logger.info("DMS storage: local")
    return _backend
