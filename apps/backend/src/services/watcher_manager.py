from __future__ import annotations

import asyncio
from pathlib import Path

from src.services.event_hub import EventHub
from src.services.watcher import FileChangeEvent, WatcherService


class WatcherManager:
    def __init__(self, hub: EventHub) -> None:
        self._hub = hub
        self._watcher: WatcherService | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start(self, path: Path) -> None:
        if self._watcher:
            self.stop()

        def _handle(event: FileChangeEvent) -> None:
            if not self._loop:
                return
            asyncio.run_coroutine_threadsafe(
                self._hub.broadcast(event.__dict__), self._loop
            )

        self._watcher = WatcherService(path, on_event=_handle)
        self._watcher.start()

    def stop(self) -> None:
        if not self._watcher:
            return
        self._watcher.stop()
        self._watcher = None

    def status(self) -> dict[str, object]:
        if not self._watcher:
            return {"running": False, "path": None}
        return {"running": self._watcher.is_running(), "path": str(self._watcher.root_path)}

    def silence(self, path: Path, ttl_seconds: float | None = None) -> None:
        if not self._watcher:
            return
        self._watcher.silence(path, ttl_seconds=ttl_seconds)


__all__ = ["WatcherManager"]
