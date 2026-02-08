from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
import re
import time
from typing import Iterable

LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+\|\s+(\w+)\s+\|\s+(.+)$"
)

_LAST_PRUNE_AT: dict[Path, float] = {}


def iter_log_entries(log_file: Path) -> Iterable[str]:
    current: list[str] = []
    with log_file.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if LOG_LINE_RE.match(line):
                if current:
                    yield "\n".join(current)
                current = [line]
                continue
            if current:
                current.append(line)
        if current:
            yield "\n".join(current)


def read_log_entries(
    log_file: Path,
    *,
    limit: int,
    offset: int,
    level: str,
    search: str,
    order: str = "desc",
) -> tuple[int, list[tuple[str, str, str]]]:
    max_items = offset + limit
    buffer: deque[tuple[str, str, str]] = deque(maxlen=max_items)
    total = 0
    level_upper = level.strip().upper()
    search_lower = search.strip().lower()
    order_normalized = order.strip().lower()
    if order_normalized not in {"asc", "desc"}:
        order_normalized = "desc"

    if order_normalized == "asc":
        start = offset
        end = offset + limit
        items: list[tuple[str, str, str]] = []
        for raw in iter_log_entries(log_file):
            first_line = raw.split("\n", 1)[0]
            match = LOG_LINE_RE.match(first_line)
            if not match:
                continue
            ts, lvl, msg = match.group(1), match.group(2), match.group(3)
            if level_upper and lvl != level_upper:
                continue
            if search_lower and search_lower not in raw.lower():
                continue
            if start <= total < end:
                items.append((ts, lvl, msg))
            total += 1
        return total, items

    for raw in iter_log_entries(log_file):
        first_line = raw.split("\n", 1)[0]
        match = LOG_LINE_RE.match(first_line)
        if not match:
            continue
        ts, lvl, msg = match.group(1), match.group(2), match.group(3)
        if level_upper and lvl != level_upper:
            continue
        if search_lower and search_lower not in raw.lower():
            continue
        total += 1
        if max_items > 0:
            buffer.append((ts, lvl, msg))

    items = list(reversed(buffer))
    page = items[offset : offset + limit]
    return total, page


def prune_log_file(
    log_file: Path,
    *,
    retention_days: int,
    min_interval_seconds: int = 300,
) -> int:
    if retention_days <= 0:
        return 0
    if not log_file.exists():
        return 0
    now = time.time()
    last = _LAST_PRUNE_AT.get(log_file)
    if last and (now - last) < min_interval_seconds:
        return 0
    _LAST_PRUNE_AT[log_file] = now

    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    kept = 0
    temp_path = log_file.with_suffix(log_file.suffix + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as output:
            for raw in iter_log_entries(log_file):
                first_line = raw.split("\n", 1)[0]
                match = LOG_LINE_RE.match(first_line)
                ts = _parse_log_timestamp(match.group(1)) if match else None
                if ts is None or ts >= cutoff:
                    output.write(raw)
                    output.write("\n")
                    kept += 1
                else:
                    removed += 1
        if removed > 0:
            temp_path.replace(log_file)
        else:
            temp_path.unlink(missing_ok=True)
    except Exception:
        temp_path.unlink(missing_ok=True)
        return 0
    return removed


def _parse_log_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


__all__ = [
    "LOG_LINE_RE",
    "iter_log_entries",
    "prune_log_file",
    "read_log_entries",
]
