from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
        search: str,
        task_id: str,
        order: str = "desc",
    ) -> tuple[int, list[SyncEventRecord]]:
        max_items = offset + limit
        total = 0
        order_normalized = order.strip().lower()
        status_filter = status.strip().lower()
        task_filter = task_id.strip()
        search_filter = search.strip().lower()

        if order_normalized not in {"asc", "desc"}:
            order_normalized = "desc"

        def matches(record: SyncEventRecord) -> bool:
            if status_filter and record.status.lower() != status_filter:
                return False
            if task_filter and record.task_id != task_filter:
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
