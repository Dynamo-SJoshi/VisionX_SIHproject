"""
WebSocket Connection Manager and Telemetry Broadcaster for BAS-HAR.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages active WebSocket telemetry connections to Mission Control dashboards."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and stores an incoming WebSocket client connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: Dict[str, Any]) -> None:
        """Broadcasts a JSON dictionary payload to all active clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_text(self, message: str) -> None:
        """Broadcasts raw text string to all active clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


# Global singleton connection manager
ws_manager = ConnectionManager()
