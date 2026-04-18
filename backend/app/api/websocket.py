"""WebSocket connection manager."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections grouped by session_id."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, session_id: uuid.UUID) -> None:
        """Accept the WebSocket and register it under the given session."""
        await websocket.accept()
        self._connections[session_id].append(websocket)
        logger.info(
            "WebSocket connected for session %s (total=%d)",
            session_id,
            len(self._connections[session_id]),
        )

    def disconnect(self, websocket: WebSocket, session_id: uuid.UUID) -> None:
        """Remove a WebSocket from the session's connection list."""
        conns = self._connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(session_id, None)
        logger.info("WebSocket disconnected for session %s", session_id)

    async def send_json(self, websocket: WebSocket, data: dict) -> None:
        """Send JSON data to a specific WebSocket."""
        try:
            await websocket.send_json(data)
        except Exception:
            logger.exception("Failed to send JSON via WebSocket")

    async def broadcast_to_session(self, session_id: uuid.UUID, data: dict) -> None:
        """Send JSON data to all connections in a session."""
        conns = self._connections.get(session_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                logger.warning("Removing dead WebSocket for session %s", session_id)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, session_id)

    def get_connections(self, session_id: uuid.UUID) -> list[WebSocket]:
        """Return the list of active connections for a session."""
        return list(self._connections.get(session_id, []))

    @property
    def active_session_count(self) -> int:
        return len(self._connections)


# Global singleton
manager = ConnectionManager()
