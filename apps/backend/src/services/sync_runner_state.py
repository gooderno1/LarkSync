from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

SyncState = Literal["idle", "running", "success", "failed", "cancelled"]
SYNC_LOG_LIMIT = 200


@dataclass
class SyncFileEvent:
    path: str
    status: str
    message: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SyncTaskStatus:
    task_id: str
    state: SyncState = "idle"
    trigger_source: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    uploaded_files: int = 0
    downloaded_files: int = 0
    deleted_files: int = 0
    conflict_files: int = 0
    delete_pending_files: int = 0
    delete_failed_files: int = 0
    last_error: str | None = None
    current_run_id: str | None = None
    last_files: list[SyncFileEvent] = field(default_factory=list)

    def record_event(self, event: SyncFileEvent, limit: int = SYNC_LOG_LIMIT) -> None:
        self.last_files.append(event)
        if len(self.last_files) > limit:
            self.last_files = self.last_files[-limit:]
