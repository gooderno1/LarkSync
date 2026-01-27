from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.services.event_hub import EventHub
from src.services.watcher_manager import WatcherManager

event_hub = EventHub()
watcher_manager = WatcherManager(event_hub)

watcher_router = APIRouter(prefix="/watcher", tags=["watcher"])
events_router = APIRouter(tags=["watcher"])


class WatcherStartRequest(BaseModel):
    path: str


class WatcherSilenceRequest(BaseModel):
    path: str
    ttl_seconds: float | None = None


@watcher_router.post("/start")
async def start_watcher(payload: WatcherStartRequest) -> dict:
    path = Path(payload.path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=400, detail="路径不存在")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")
    watcher_manager.start(path)
    return {"status": "started", "path": str(path)}


@watcher_router.post("/stop")
async def stop_watcher() -> dict:
    watcher_manager.stop()
    return {"status": "stopped"}


@watcher_router.get("/status")
async def watcher_status() -> dict:
    return watcher_manager.status()


@watcher_router.post("/silence")
async def silence_path(payload: WatcherSilenceRequest) -> dict:
    path = Path(payload.path).expanduser()
    watcher_manager.silence(path, ttl_seconds=payload.ttl_seconds)
    return {"status": "ok"}


@events_router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await event_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await event_hub.disconnect(websocket)
