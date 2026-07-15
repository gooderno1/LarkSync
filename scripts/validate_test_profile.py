from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


class SnapshotValidationError(RuntimeError):
    pass


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        is not None
    )


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(connection, table):
        return set()
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def validate_snapshot(data_dir: Path, *, profile: str) -> dict[str, Any]:
    root = data_dir.expanduser().resolve()
    if profile != "snapshot_test":
        raise SnapshotValidationError("快照目录只能使用 snapshot_test 配置档")
    database = root / "larksync.db"
    manifest_path = root / "snapshot-manifest.json"
    workspace = (root / "workspace").resolve()
    if not database.is_file() or not manifest_path.is_file() or not workspace.is_dir():
        raise SnapshotValidationError("快照缺少数据库、manifest 或 workspace")

    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        enabled_tasks = 0
        escaped_paths: list[str] = []
        if "enabled" in _columns(connection, "sync_tasks"):
            enabled_tasks = int(
                connection.execute("SELECT COUNT(*) FROM sync_tasks WHERE enabled != 0").fetchone()[0]
            )
        if "local_path" in _columns(connection, "sync_tasks"):
            for (raw_path,) in connection.execute("SELECT local_path FROM sync_tasks"):
                resolved = Path(str(raw_path)).expanduser().resolve()
                if not resolved.is_relative_to(workspace):
                    escaped_paths.append(str(resolved))
        running_runs = 0
        if "state" in _columns(connection, "sync_runs"):
            running_runs = int(
                connection.execute("SELECT COUNT(*) FROM sync_runs WHERE state = 'running'").fetchone()[0]
            )
    finally:
        connection.close()

    if integrity.lower() != "ok":
        raise SnapshotValidationError(f"数据库完整性校验失败: {integrity}")
    if enabled_tasks:
        raise SnapshotValidationError(f"快照仍有 {enabled_tasks} 个启用任务")
    if running_runs:
        raise SnapshotValidationError(f"快照仍有 {running_runs} 条 running 运行记录")
    if escaped_paths:
        raise SnapshotValidationError(f"任务路径逃逸快照 workspace: {escaped_paths[0]}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "valid": True,
        "profile": profile,
        "data_dir": str(root),
        "database": str(database),
        "schema_version": manifest.get("schema_version"),
        "enabled_tasks": enabled_tasks,
        "running_runs": running_runs,
        "integrity_check": integrity,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 LarkSync 测试运行配置")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--data-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = validate_snapshot(args.data_dir, profile=args.profile)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
