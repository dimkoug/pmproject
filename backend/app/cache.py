"""Redis cache helper — thin async wrapper used by routers for read-through caching."""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return a shared Redis connection pool (lazy-init)."""
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def cache_get(key: str) -> Any | None:
    """Get a JSON-serialised value from Redis. Returns None on miss or error."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception:
        logger.warning("Redis cache_get failed for key=%s", key, exc_info=True)
    return None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Store a JSON-serialisable value with a TTL (seconds)."""
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("Redis cache_set failed for key=%s", key, exc_info=True)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g. 'dashboard:*')."""
    try:
        r = await get_redis()
        cursor = None
        while cursor != 0:
            cursor, keys = await r.scan(cursor=cursor or 0, match=pattern, count=200)
            if keys:
                await r.delete(*keys)
    except Exception:
        logger.warning("Redis cache_delete_pattern failed for %s", pattern, exc_info=True)
