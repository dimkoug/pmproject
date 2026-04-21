"""WebSocket connection manager with Redis pub/sub for multi-worker broadcasting.

When running multiple uvicorn workers, each worker only sees its own WebSocket
connections. Redis pub/sub ensures broadcasts reach ALL workers/connections.
"""

import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._pubsub_task: asyncio.Task | None = None
        self._redis_available: bool = False

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

        # Start Redis subscriber lazily on first connection
        if self._pubsub_task is None:
            self._pubsub_task = asyncio.create_task(self._redis_subscriber())

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, event: str, data: dict):
        """Publish to Redis so all workers send to their local connections."""
        message = json.dumps({"project_id": project_id, "event": event, "data": data})

        # Try Redis pub/sub first (multi-worker)
        if await self._publish_to_redis(message):
            return

        # Fallback: local-only broadcast (single worker)
        await self._local_broadcast(project_id, event, data)

    async def broadcast_all(self, event: str, data: dict):
        """Broadcast to every connected client across all projects."""
        message = json.dumps({"project_id": "__all__", "event": event, "data": data})

        if await self._publish_to_redis(message):
            return

        # Fallback: local
        payload = json.dumps({"event": event, "data": data})
        for connections in self.active_connections.values():
            for conn in connections:
                try:
                    await conn.send_text(payload)
                except Exception:
                    pass

    # ── Internal helpers ─────────────────────────────────────────────

    async def _local_broadcast(self, project_id: str, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        if project_id in self.active_connections:
            for conn in self.active_connections[project_id]:
                try:
                    await conn.send_text(payload)
                except Exception:
                    pass

    async def _publish_to_redis(self, message: str) -> bool:
        """Publish a message to the ws:broadcast channel. Returns False if Redis unavailable."""
        try:
            from app.cache import get_ws_redis
            r = await get_ws_redis()
            await r.publish("ws:broadcast", message)
            return True
        except Exception:
            return False

    async def _redis_subscriber(self):
        """Background task that subscribes to Redis and pushes to local WebSockets."""
        try:
            from app.cache import get_ws_redis
            r = await get_ws_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe("ws:broadcast")
            self._redis_available = True
            logger.info("WebSocket Redis subscriber started")

            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                try:
                    envelope = json.loads(raw_message["data"])
                    project_id = envelope.get("project_id")
                    event = envelope.get("event")
                    data = envelope.get("data")

                    if project_id == "__all__":
                        payload = json.dumps({"event": event, "data": data})
                        for conns in self.active_connections.values():
                            for conn in conns:
                                try:
                                    await conn.send_text(payload)
                                except Exception:
                                    pass
                    else:
                        await self._local_broadcast(project_id, event, data)
                except Exception:
                    logger.warning("Error handling Redis WS message", exc_info=True)
        except Exception:
            logger.info("Redis pub/sub not available, falling back to local-only WS")
            self._redis_available = False


manager = ConnectionManager()
