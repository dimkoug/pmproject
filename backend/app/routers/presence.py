"""Real-time presence — who's currently viewing a task, document, or opp.

Backed by Redis (cache instance) with TTL-based sliding window. Frontend
heartbeats every 20s; entries expire after 45s so idle tabs drop off quickly.
Works across backend replicas because state lives in Redis, not process memory.
"""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/presence", tags=["presence"], dependencies=[Depends(get_current_user)])

HEARTBEAT_TTL = 45  # seconds — if no heartbeat within this window the user drops off


def _key(entity_type: str, entity_id: str) -> str:
    return f"presence:{entity_type}:{entity_id}"


@router.post("/{entity_type}/{entity_id}")
async def heartbeat(entity_type: str, entity_id: str, current_user: User = Depends(get_current_user)):
    """Record / refresh this user's presence on an entity. Called every 20s by the UI."""
    r = await get_redis()
    key = _key(entity_type, entity_id)
    member = json.dumps({
        "user_id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
    })
    # Hash-per-entity with per-user field; Redis will auto-expire the whole key after HEARTBEAT_TTL
    # If multiple users are present we want them to independently expire — use a sorted set
    # of user_id -> json with score = timestamp, and let clients filter stale entries.
    import time
    now = time.time()
    await r.zadd(key, {member: now})
    await r.expire(key, 300)  # safety cap; we prune stale members on read
    return {"ok": True}


@router.get("/{entity_type}/{entity_id}")
async def who_is_viewing(entity_type: str, entity_id: str, current_user: User = Depends(get_current_user)):
    """Return all users whose last heartbeat was within HEARTBEAT_TTL seconds."""
    r = await get_redis()
    key = _key(entity_type, entity_id)
    import time
    cutoff = time.time() - HEARTBEAT_TTL
    # Remove stale members then read
    await r.zremrangebyscore(key, "-inf", cutoff)
    members = await r.zrange(key, 0, -1, withscores=True)
    viewers = []
    seen = set()
    for raw, ts in members:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        uid = payload.get("user_id")
        if not uid or uid in seen:
            continue
        seen.add(uid)
        viewers.append({**payload, "last_seen": ts})
    return {"viewers": viewers, "count": len(viewers)}


@router.delete("/{entity_type}/{entity_id}")
async def leave(entity_type: str, entity_id: str, current_user: User = Depends(get_current_user)):
    """Explicit leave — called on page unmount."""
    r = await get_redis()
    key = _key(entity_type, entity_id)
    # Remove any member with this user_id (match by prefix in JSON)
    members = await r.zrange(key, 0, -1)
    to_remove = [m for m in members if f'"user_id": "{current_user.id}"' in m]
    if to_remove:
        await r.zrem(key, *to_remove)
    return {"ok": True}
