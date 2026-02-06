from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class FileChangeEvent:
    event_type: str
    src_path: str
    dest_path: str | None
    timestamp: float


class DebounceFilter:
    def __init__(self, window_seconds: float = 2.0) -> None:
        self._window = window_seconds
        self._last_seen: dict[str, float] = {}

    def should_emit(self, path: str, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        last = self._last_seen.get(path)
        self._last_seen[path] = now
        if last is None:
            return True
        return (now - last) >= self._window


class IgnoreRegistry:
    def __init__(self, ttl_seconds: float = 5.0) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, float] = {}

    def add(self, path: str, ttl_seconds: float | None = None, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        self._entries[path] = now + ttl

    def is_ignored(self, path: str, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        expires_at = self._entries.get(path)
        if expires_at is None:
            return False
        if expires_at < now:
            self._entries.pop(path, None)
            return False
        return True


class FileEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_event: Callable[[FileChangeEvent], None],
        debounce: DebounceFilter,
        ignore: IgnoreRegistry,
    ) -> None:
        super().__init__()
        self._on_event = on_event
        self._debounce = debounce
        self._ignore = ignore

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        src_path = str(getattr(event, "src_path", "")) or ""
        dest_path = getattr(event, "dest_path", None)
        dest_path_str = str(dest_path) if dest_path else ""
        primary_path = dest_path_str or src_path
        if not primary_path:
            return
        if (
            (src_path and self._ignore.is_ignored(src_path))
            or (dest_path_str and self._ignore.is_ignored(dest_path_str))
            or self._ignore.is_ignored(primary_path)
        ):
            return
        if not self._debounce.should_emit(primary_path):
            return
        payload = FileChangeEvent(
            event_type=str(getattr(event, "event_type", "unknown")),
            src_path=src_path,
            dest_path=dest_path_str if dest_path_str else None,
            timestamp=time.time(),
        )
        self._on_event(payload)


class WatcherService:
    def __init__(
        self,
        root_path: Path,
        on_event: Callable[[FileChangeEvent], None],
        debounce_seconds: float = 2.0,
        ignore_seconds: float = 5.0,
    ) -> None:
        self._root_path = root_path
        self._debounce = DebounceFilter(window_seconds=debounce_seconds)
        self._ignore = IgnoreRegistry(ttl_seconds=ignore_seconds)
        self._handler = FileEventHandler(on_event, self._debounce, self._ignore)
        self._observer = Observer()

    @property
    def root_path(self) -> Path:
        return self._root_path

    def start(self) -> None:
        self._observer.schedule(self._handler, str(self._root_path), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=5)

    def silence(self, path: Path, ttl_seconds: float | None = None) -> None:
        self._ignore.add(str(path), ttl_seconds=ttl_seconds)

    def is_running(self) -> bool:
        return self._observer.is_alive()


__all__ = [
    "DebounceFilter",
    "FileChangeEvent",
    "IgnoreRegistry",
    "WatcherService",
]
