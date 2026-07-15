from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any


TOKEN_COLUMNS: dict[str, tuple[str, ...]] = {
    "sync_tasks": ("cloud_folder_token",),
    "sync_links": ("cloud_token", "cloud_parent_token"),
    "sync_tombstones": ("cloud_token",),
    "sync_mappings": ("feishu_token",),
    "conflicts": ("cloud_token",),
    "sync_block_states": ("cloud_token",),
}
PATH_COLUMNS: dict[str, tuple[str, ...]] = {
    "sync_mappings": ("local_path",),
    "sync_links": ("local_path",),
    "sync_tombstones": ("local_path",),
    "conflicts": ("local_path",),
    "sync_run_events": ("path",),
    "sync_block_states": ("local_path",),
}


class SnapshotExportError(RuntimeError):
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


def _pseudonym(value: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:24]
    return f"snapshot_{digest}"


def _safe_basename(value: str) -> str:
    normalized = value.replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1].strip()
    return name or "item"


def _redacted_path(workspace: Path, value: str, salt: str) -> str:
    bucket = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:12]
    return str((workspace / "redacted" / bucket / _safe_basename(value)).resolve())


def _update_column_values(
    connection: sqlite3.Connection,
    *,
    table: str,
    column: str,
    transform,
) -> None:
    if column not in _columns(connection, table):
        return
    rows = connection.execute(
        f'SELECT rowid, "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
    ).fetchall()
    for rowid, value in rows:
        connection.execute(
            f'UPDATE "{table}" SET "{column}" = ? WHERE rowid = ?',
            (transform(str(value)), rowid),
        )


def _sanitize_snapshot(
    connection: sqlite3.Connection,
    *,
    workspace: Path,
    exported_at: float,
    salt: str,
) -> None:
    task_columns = _columns(connection, "sync_tasks")
    if task_columns:
        task_rows = connection.execute('SELECT rowid, id FROM "sync_tasks"').fetchall()
        for rowid, task_id in task_rows:
            task_workspace = (workspace / "tasks" / str(task_id)).resolve()
            task_workspace.mkdir(parents=True, exist_ok=True)
            assignments = []
            values: list[Any] = []
            if "local_path" in task_columns:
                assignments.append('"local_path" = ?')
                values.append(str(task_workspace))
            if "base_path" in task_columns:
                assignments.append('"base_path" = ?')
                values.append(str(task_workspace))
            if "enabled" in task_columns:
                assignments.append('"enabled" = 0')
            if "owner_open_id" in task_columns:
                assignments.append('"owner_open_id" = NULL')
            if assignments:
                connection.execute(
                    f'UPDATE "sync_tasks" SET {", ".join(assignments)} WHERE rowid = ?',
                    (*values, rowid),
                )

    run_columns = _columns(connection, "sync_runs")
    if {"state", "finished_at", "last_error"}.issubset(run_columns):
        assignments = [
            '"state" = \'cancelled\'',
            '"finished_at" = ?',
            '"last_error" = ?',
        ]
        values: list[Any] = [
            exported_at,
            "快照导出时检测到遗留运行，已标记为中断",
        ]
        if "last_event_at" in run_columns:
            assignments.append('"last_event_at" = ?')
            values.append(exported_at)
        if "updated_at" in run_columns:
            assignments.append('"updated_at" = ?')
            values.append(exported_at)
        connection.execute(
            f'UPDATE "sync_runs" SET {", ".join(assignments)} WHERE "state" = \'running\'',
            values,
        )

    for table, columns in TOKEN_COLUMNS.items():
        for column in columns:
            _update_column_values(
                connection,
                table=table,
                column=column,
                transform=lambda value, current_salt=salt: _pseudonym(value, current_salt),
            )
    for table, columns in PATH_COLUMNS.items():
        for column in columns:
            _update_column_values(
                connection,
                table=table,
                column=column,
                transform=lambda value, current_salt=salt: _redacted_path(
                    workspace, value, current_salt
                ),
            )

    for column in ("local_preview", "cloud_preview"):
        if column in _columns(connection, "conflicts"):
            connection.execute(f'UPDATE "conflicts" SET "{column}" = NULL')


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in tables
    }


def export_snapshot(
    source_db: Path,
    output_dir: Path,
    *,
    exported_at: float | None = None,
) -> dict[str, Any]:
    source = source_db.expanduser().resolve()
    output = output_dir.expanduser().resolve()
    if not source.is_file():
        raise SnapshotExportError(f"源数据库不存在: {source}")
    if output == source.parent or source.is_relative_to(output):
        raise SnapshotExportError("快照输出目录不能包含源数据库")
    if output.exists() and any(output.iterdir()):
        raise SnapshotExportError(f"快照输出目录必须为空: {output}")

    output.mkdir(parents=True, exist_ok=True)
    workspace = output / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    destination = output / "larksync.db"
    timestamp = time.time() if exported_at is None else float(exported_at)
    salt = secrets.token_hex(16)

    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        _sanitize_snapshot(
            destination_connection,
            workspace=workspace,
            exported_at=timestamp,
            salt=salt,
        )
        destination_connection.commit()
        integrity = str(destination_connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            raise SnapshotExportError(f"快照数据库完整性校验失败: {integrity}")
        schema_version = None
        if _table_exists(destination_connection, "sync_meta"):
            row = destination_connection.execute(
                "SELECT value FROM sync_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is not None:
                try:
                    schema_version = int(row[0])
                except (TypeError, ValueError):
                    schema_version = None
        counts = _table_counts(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()

    manifest: dict[str, Any] = {
        "format_version": 1,
        "exported_at": timestamp,
        "source_database": str(source),
        "snapshot_database": str(destination),
        "schema_version": schema_version,
        "integrity_check": "ok",
        "table_counts": counts,
        "redaction_rules": {
            "tasks": "disabled_and_local_paths_remapped",
            "running_runs": "cancelled_as_interrupted",
            "tokens": "stable_sha256_pseudonym",
            "owner_open_id": "removed",
            "conflict_previews": "removed",
            "paths": "remapped_under_snapshot_workspace",
            "credentials": "not_exported",
        },
    }
    (output / "snapshot-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出 LarkSync 脱敏测试快照")
    parser.add_argument("--source-db", type=Path, help="明确指定正式数据库路径")
    parser.add_argument("--source-profile", choices=["production"], help="源配置档标识")
    parser.add_argument("--output", required=True, type=Path, help="快照输出目录")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_db = args.source_db
    if source_db is None and args.source_profile == "production":
        env_path = os.getenv("LARKSYNC_PRODUCTION_DB_PATH")
        if env_path:
            source_db = Path(env_path)
    if source_db is None:
        raise SnapshotExportError(
            "无法安全确认正式数据库；请使用 --source-db，或设置 LARKSYNC_PRODUCTION_DB_PATH"
        )
    manifest = export_snapshot(source_db, args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
