from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
import tracemalloc
from pathlib import Path
from typing import Any


DEFAULT_MAX_P95_MS = 250.0
DEFAULT_MAX_PEAK_MEMORY_MB = 256.0


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        is not None
    )


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * percentile) - 1)
    return ordered[index]


def benchmark_snapshot(
    database: Path,
    *,
    iterations: int = 20,
    max_p95_ms: float = DEFAULT_MAX_P95_MS,
    max_peak_memory_mb: float = DEFAULT_MAX_PEAK_MEMORY_MB,
) -> dict[str, Any]:
    db_path = database.expanduser().resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"快照数据库不存在: {db_path}")
    safe_iterations = max(1, int(iterations))
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    queries = {
        "task_list": (
            "sync_tasks",
            "SELECT * FROM sync_tasks ORDER BY updated_at DESC LIMIT 500"
            if "updated_at" in {row[1] for row in connection.execute("PRAGMA table_info(sync_tasks)")}
            else "SELECT * FROM sync_tasks LIMIT 500",
        ),
        "latest_runs": (
            "sync_runs",
            "SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 500"
            if "started_at" in {row[1] for row in connection.execute("PRAGMA table_info(sync_runs)")}
            else "SELECT * FROM sync_runs LIMIT 500",
        ),
        "recent_events": (
            "sync_run_events",
            "SELECT * FROM sync_run_events ORDER BY timestamp DESC LIMIT 2000",
        ),
    }

    tracemalloc.start()
    query_report: dict[str, dict[str, float | int | bool]] = {}
    try:
        for name, (table, sql) in queries.items():
            if not _table_exists(connection, table):
                query_report[name] = {
                    "available": False,
                    "rows": 0,
                    "mean_ms": 0.0,
                    "p95_ms": 0.0,
                    "max_ms": 0.0,
                }
                continue
            durations: list[float] = []
            row_count = 0
            for _ in range(safe_iterations):
                started = time.perf_counter()
                rows = connection.execute(sql).fetchall()
                durations.append((time.perf_counter() - started) * 1000)
                row_count = len(rows)
            query_report[name] = {
                "available": True,
                "rows": row_count,
                "mean_ms": sum(durations) / len(durations),
                "p95_ms": _percentile(durations, 0.95),
                "max_ms": max(durations),
            }
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        connection.close()

    available_p95 = [
        float(item["p95_ms"])
        for item in query_report.values()
        if item["available"]
    ]
    slowest_p95 = max(available_p95, default=0.0)
    memory_limit_bytes = int(max_peak_memory_mb * 1024 * 1024)
    return {
        "database": str(db_path),
        "database_size_bytes": db_path.stat().st_size,
        "iterations": safe_iterations,
        "peak_memory_bytes": peak_memory,
        "thresholds": {
            "max_p95_ms": max_p95_ms,
            "max_peak_memory_mb": max_peak_memory_mb,
        },
        "queries": query_report,
        "passed": slowest_p95 <= max_p95_ms and peak_memory <= memory_limit_bytes,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="基准测试 LarkSync 脱敏快照查询性能")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--max-p95-ms", type=float, default=DEFAULT_MAX_P95_MS)
    parser.add_argument(
        "--max-peak-memory-mb", type=float, default=DEFAULT_MAX_PEAK_MEMORY_MB
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = benchmark_snapshot(
        args.database,
        iterations=args.iterations,
        max_p95_ms=args.max_p95_ms,
        max_peak_memory_mb=args.max_peak_memory_mb,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
