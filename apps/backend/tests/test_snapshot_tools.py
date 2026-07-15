from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_test_snapshot import export_snapshot
from scripts.benchmark_snapshot import benchmark_snapshot
from scripts.validate_test_profile import SnapshotValidationError, validate_snapshot


def _create_source_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE sync_meta (key TEXT PRIMARY KEY, value TEXT, updated_at REAL NOT NULL);
        CREATE TABLE sync_tasks (
            id TEXT PRIMARY KEY,
            name TEXT,
            local_path TEXT NOT NULL,
            cloud_folder_token TEXT NOT NULL,
            base_path TEXT,
            owner_open_id TEXT,
            enabled INTEGER NOT NULL
        );
        CREATE TABLE sync_runs (
            run_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            state TEXT NOT NULL,
            finished_at REAL,
            last_event_at REAL,
            last_error TEXT,
            updated_at REAL NOT NULL
        );
        CREATE TABLE conflicts (
            id TEXT PRIMARY KEY,
            local_path TEXT NOT NULL,
            cloud_token TEXT NOT NULL,
            local_preview TEXT,
            cloud_preview TEXT
        );
        INSERT INTO sync_meta VALUES ('schema_version', '1', 1);
        INSERT INTO sync_tasks VALUES (
            'task-1', '真实任务', 'D:/Formal/Private', 'fld_secret', 'D:/Formal', 'ou_secret', 1
        );
        INSERT INTO sync_runs VALUES (
            'run-1', 'task-1', 'running', NULL, NULL, NULL, 10
        );
        INSERT INTO conflicts VALUES (
            'conflict-1', 'D:/Formal/Private/秘密.md', 'doc_secret', '正文A', '正文B'
        );
        """
    )
    connection.commit()
    connection.close()


def test_export_snapshot_uses_online_backup_and_redacts_runtime_data(tmp_path: Path) -> None:
    source = tmp_path / "formal.db"
    output = tmp_path / "snapshot"
    _create_source_database(source)

    manifest = export_snapshot(source, output, exported_at=100.0)

    snapshot_db = output / "larksync.db"
    assert snapshot_db.exists()
    connection = sqlite3.connect(snapshot_db)
    task = connection.execute(
        "SELECT local_path, base_path, cloud_folder_token, owner_open_id, enabled FROM sync_tasks"
    ).fetchone()
    run = connection.execute(
        "SELECT state, finished_at, last_error FROM sync_runs WHERE run_id = 'run-1'"
    ).fetchone()
    conflict = connection.execute(
        "SELECT local_path, cloud_token, local_preview, cloud_preview FROM conflicts"
    ).fetchone()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    connection.close()

    assert task is not None
    assert Path(task[0]).is_relative_to(output / "workspace")
    assert Path(task[1]).is_relative_to(output / "workspace")
    assert task[2].startswith("snapshot_")
    assert task[3] is None
    assert task[4] == 0
    assert run == ("cancelled", 100.0, "快照导出时检测到遗留运行，已标记为中断")
    assert conflict is not None
    assert Path(conflict[0]).is_relative_to(output / "workspace")
    assert conflict[1].startswith("snapshot_")
    assert conflict[2:] == (None, None)
    assert integrity == "ok"
    assert manifest["schema_version"] == 1
    assert manifest["table_counts"]["sync_tasks"] == 1
    assert manifest["redaction_rules"]["tokens"] == "stable_sha256_pseudonym"
    assert json.loads((output / "snapshot-manifest.json").read_text(encoding="utf-8")) == manifest


def test_validate_snapshot_rejects_enabled_tasks(tmp_path: Path) -> None:
    source = tmp_path / "formal.db"
    output = tmp_path / "snapshot"
    _create_source_database(source)
    export_snapshot(source, output)

    report = validate_snapshot(output, profile="snapshot_test")
    assert report["valid"] is True
    assert report["enabled_tasks"] == 0
    assert report["running_runs"] == 0

    connection = sqlite3.connect(output / "larksync.db")
    connection.execute("UPDATE sync_tasks SET enabled = 1")
    connection.commit()
    connection.close()

    with pytest.raises(SnapshotValidationError, match="启用任务"):
        validate_snapshot(output, profile="snapshot_test")


def test_benchmark_snapshot_reports_query_latency_and_memory(tmp_path: Path) -> None:
    source = tmp_path / "formal.db"
    output = tmp_path / "snapshot"
    _create_source_database(source)
    export_snapshot(source, output)

    report = benchmark_snapshot(output / "larksync.db", iterations=3)

    assert report["iterations"] == 3
    assert report["database_size_bytes"] > 0
    assert report["peak_memory_bytes"] > 0
    assert report["queries"]["task_list"]["p95_ms"] >= 0
    assert report["passed"] is True
