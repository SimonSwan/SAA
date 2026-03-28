"""WebSocket support for live state streaming to connected SIO clients."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

ws_router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Tracks active WebSocket connections per session and broadcasts updates."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(session_id, []).append(ws)
        logger.info("WebSocket connected for session %s", session_id)

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(session_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(session_id, None)
        logger.info("WebSocket disconnected for session %s", session_id)

    async def broadcast(self, session_id: str, data: dict[str, Any]) -> None:
        """Send *data* as JSON to every client connected to *session_id*."""
        conns = self._connections.get(session_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


# Module-level singleton so routes can import and use it.
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@ws_router.websocket("/ws/{session_id}")
async def ws_session(ws: WebSocket, session_id: str) -> None:
    """Stream live state updates for *session_id*.

    On connect the current state snapshot is sent immediately.  The client
    then receives a JSON message after every interaction that mutates state.
    """
    # Import here to avoid circular dependency at module level.
    from saa.sio.api.routes import session_manager  # noqa: WPS433

    await manager.connect(session_id, ws)

    try:
        # Send the current snapshot on connect.
        state = session_manager.get_state(session_id)
        if state is not None:
            await ws.send_json(state.model_dump())

        # Keep the connection alive — the client can also send messages
        # (future: commands), but for now we just wait for disconnect.
        while True:
            # Await incoming messages so the connection stays open.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session_id, ws)
