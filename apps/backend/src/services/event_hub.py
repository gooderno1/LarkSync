from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class EventHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, account_id: str | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = account_id

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        async with self._lock:
            connections = list(self._connections.items())
        payload_account_id = str(payload.get("account_id") or "").strip() or None
        for websocket, subscribed_account_id in connections:
            if subscribed_account_id and subscribed_account_id != payload_account_id:
                continue
            try:
                await websocket.send_text(message)
            except Exception:
                await self.disconnect(websocket)


__all__ = ["EventHub"]
