from __future__ import annotations

from collections import deque
from pathlib import Path
import re
from typing import Iterable

LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+\|\s+(\w+)\s+\|\s+(.+)$"
)


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


__all__ = ["LOG_LINE_RE", "iter_log_entries", "read_log_entries"]
