from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Iterable


@dataclass
class ConflictItem:
    id: str
    local_path: str
    cloud_token: str
    local_hash: str
    db_hash: str
    cloud_version: int
    db_version: int
    local_preview: str | None
    cloud_preview: str | None
    created_at: float
    resolved: bool = False
    resolved_action: str | None = None


class ConflictService:
    def __init__(self) -> None:
        self._items: dict[str, ConflictItem] = {}

    def detect_and_add(
        self,
        *,
        local_path: str,
        cloud_token: str,
        local_hash: str,
        db_hash: str,
        cloud_version: int,
        db_version: int,
        local_preview: str | None = None,
        cloud_preview: str | None = None,
    ) -> ConflictItem | None:
        if local_hash != db_hash and cloud_version > db_version:
            return self.add_conflict(
                local_path=local_path,
                cloud_token=cloud_token,
                local_hash=local_hash,
                db_hash=db_hash,
                cloud_version=cloud_version,
                db_version=db_version,
                local_preview=local_preview,
                cloud_preview=cloud_preview,
            )
        return None

    def add_conflict(
        self,
        *,
        local_path: str,
        cloud_token: str,
        local_hash: str,
        db_hash: str,
        cloud_version: int,
        db_version: int,
        local_preview: str | None = None,
        cloud_preview: str | None = None,
    ) -> ConflictItem:
        conflict = ConflictItem(
            id=str(uuid.uuid4()),
            local_path=local_path,
            cloud_token=cloud_token,
            local_hash=local_hash,
            db_hash=db_hash,
            cloud_version=cloud_version,
            db_version=db_version,
            local_preview=local_preview,
            cloud_preview=cloud_preview,
            created_at=time.time(),
        )
        self._items[conflict.id] = conflict
        return conflict

    def list_conflicts(self, include_resolved: bool = False) -> list[ConflictItem]:
        items: Iterable[ConflictItem] = self._items.values()
        if not include_resolved:
            items = [item for item in items if not item.resolved]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def resolve(self, conflict_id: str, action: str) -> ConflictItem | None:
        conflict = self._items.get(conflict_id)
        if not conflict:
            return None
        conflict.resolved = True
        conflict.resolved_action = action
        return conflict
