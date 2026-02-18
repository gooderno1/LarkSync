from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import time

from loguru import logger

from src.core.paths import logs_dir


@dataclass(frozen=True)
class SyncEventRecord:
    timestamp: float
    task_id: str
    task_name: str
    status: str
    path: str
    message: str | None = None


class SyncEventStore:
    def __init__(self, log_file: Path | None = None) -> None:
        self._log_file = log_file or (logs_dir() / "sync-events.jsonl")
        self._last_pruned_at: float | None = None

    @property
    def log_file(self) -> Path:
        return self._log_file

    def append(self, record: SyncEventRecord) -> None:
        payload = {
            "timestamp": float(record.timestamp),
            "task_id": record.task_id,
            "task_name": record.task_name,
            "status": record.status,
            "path": record.path,
            "message": record.message,
        }
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with self._log_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False))
                handle.write("\n")
        except Exception:
            logger.exception("同步日志写入失败")

    def iter_records(self) -> Iterable[SyncEventRecord]:
        if not self._log_file.exists():
            return []
        records: list[SyncEventRecord] = []
        try:
            with self._log_file.open("r", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    record = _record_from_payload(payload)
                    if record is None:
                        continue
                    records.append(record)
        except Exception:
            logger.exception("同步日志读取失败")
            return []
        return records

    def read_events(
        self,
        *,
        limit: int,
        offset: int,
        status: str,
        statuses: list[str] | None = None,
        search: str,
        task_id: str,
        task_ids: list[str] | None = None,
        order: str = "desc",
    ) -> tuple[int, list[SyncEventRecord]]:
        max_items = offset + limit
        total = 0
        order_normalized = order.strip().lower()
        status_filter = status.strip().lower()
        task_filter = task_id.strip()
        status_filters = {
            value.strip().lower() for value in (statuses or []) if value and value.strip()
        }
        task_filters = {
            value.strip() for value in (task_ids or []) if value and value.strip()
        }
        if status_filter:
            status_filters.add(status_filter)
        if task_filter:
            task_filters.add(task_filter)
        search_filter = search.strip().lower()

        if order_normalized not in {"asc", "desc"}:
            order_normalized = "desc"

        def matches(record: SyncEventRecord) -> bool:
            if status_filters and record.status.lower() not in status_filters:
                return False
            if task_filters and record.task_id not in task_filters:
                return False
            if not search_filter:
                return True
            target = " ".join(
                [
                    record.task_name,
                    record.path,
                    record.message or "",
                ]
            ).lower()
            return search_filter in target

        if order_normalized == "asc":
            items: list[SyncEventRecord] = []
            start = offset
            end = offset + limit
            for record in self._iter_records_stream():
                if not matches(record):
                    continue
                if start <= total < end:
                    items.append(record)
                total += 1
            return total, items

        from collections import deque

        buffer: deque[SyncEventRecord] = deque(maxlen=max_items)
        for record in self._iter_records_stream():
            if not matches(record):
                continue
            total += 1
            if max_items > 0:
                buffer.append(record)
        items = list(reversed(buffer))
        page = items[offset : offset + limit]
        return total, page

    def prune(self, *, retention_days: int, min_interval_seconds: int = 300) -> int:
        if retention_days <= 0:
            return 0
        if not self._log_file.exists():
            return 0
        now = time.time()
        if (
            self._last_pruned_at is not None
            and now - self._last_pruned_at < min_interval_seconds
        ):
            return 0
        self._last_pruned_at = now
        cutoff = now - retention_days * 86400
        removed = 0
        temp_path = self._log_file.with_suffix(self._log_file.suffix + ".tmp")
        try:
            with self._log_file.open("r", encoding="utf-8", errors="replace") as source, \
                    temp_path.open("w", encoding="utf-8") as target:
                for raw in source:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        target.write(raw)
                        continue
                    try:
                        timestamp = float(payload.get("timestamp") or 0.0)
                    except (TypeError, ValueError):
                        timestamp = 0.0
                    if timestamp >= cutoff:
                        target.write(json.dumps(payload, ensure_ascii=False))
                        target.write("\n")
                    else:
                        removed += 1
            if removed > 0:
                temp_path.replace(self._log_file)
            else:
                temp_path.unlink(missing_ok=True)
        except Exception:
            temp_path.unlink(missing_ok=True)
            return 0
        return removed

    def file_size_bytes(self) -> int:
        try:
            return self._log_file.stat().st_size
        except FileNotFoundError:
            return 0

    def _iter_records_stream(self) -> Iterable[SyncEventRecord]:
        if not self._log_file.exists():
            return []
        try:
            with self._log_file.open("r", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    record = _record_from_payload(payload)
                    if record is None:
                        continue
                    yield record
        except Exception:
            logger.exception("同步日志读取失败")
            return []


def _record_from_payload(payload: object) -> SyncEventRecord | None:
    if not isinstance(payload, dict):
        return None
    try:
        timestamp = float(payload.get("timestamp") or 0.0)
    except (TypeError, ValueError):
        timestamp = 0.0
    task_id = str(payload.get("task_id") or "")
    task_name = str(payload.get("task_name") or "未命名任务")
    status = str(payload.get("status") or "")
    path = str(payload.get("path") or "")
    message = payload.get("message")
    if message is not None:
        message = str(message)
    if not task_id or not status or not path:
        return None
    return SyncEventRecord(
        timestamp=timestamp,
        task_id=task_id,
        task_name=task_name,
        status=status,
        path=path,
        message=message,
    )


__all__ = ["SyncEventRecord", "SyncEventStore"]
