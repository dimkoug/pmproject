"""Redis clients — separate pools for cache vs. WebSocket pub/sub.

The cache pool backs the read-through helpers here. The ws pool is consumed by
`app.websockets.manager` for broadcast fan-out across backend replicas. Keeping
them separate means a flood of WS events can't evict cache entries and vice
versa — each Redis has its own `maxmemory` policy in docker-compose.yml.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_cache_pool: aioredis.Redis | None = None
_ws_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the cache Redis pool (lazy-init)."""
    global _cache_pool
    if _cache_pool is None:
        _cache_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _cache_pool


async def get_ws_redis() -> aioredis.Redis:
    """Return the WebSocket pub/sub Redis pool (lazy-init, may share cache URL)."""
    global _ws_pool
    if _ws_pool is None:
        _ws_pool = aioredis.from_url(
            settings.effective_redis_ws_url,
            decode_responses=True,
            max_connections=20,
        )
    return _ws_pool


async def close_redis() -> None:
    """Tear down both Redis connection pools. Called from lifespan on app
    shutdown so sockets close cleanly before the process exits."""
    global _cache_pool, _ws_pool
    if _cache_pool is not None:
        await _cache_pool.aclose()
        _cache_pool = None
    if _ws_pool is not None:
        await _ws_pool.aclose()
        _ws_pool = None


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
