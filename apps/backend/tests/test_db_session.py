from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from src.db.session import (
    CURRENT_SCHEMA_VERSION,
    _backup_corrupt_db,
    _extract_sqlite_path,
    _is_sqlite_corrupt_error,
    _sqlite_literal,
    create_engine,
    dispose_engines,
    get_session_maker,
    init_db,
)
from src.services.sync_run_service import SyncRunService


def test_sqlite_literal_string() -> None:
    assert _sqlite_literal("auto") == "'auto'"
    assert _sqlite_literal("a'b") == "'a''b'"


def test_sqlite_literal_numbers_and_bool() -> None:
    assert _sqlite_literal(3) == "3"
    assert _sqlite_literal(3.5) == "3.5"
    assert _sqlite_literal(True) == "1"
    assert _sqlite_literal(False) == "0"


def test_sqlite_literal_none() -> None:
    assert _sqlite_literal(None) == "NULL"


def test_is_sqlite_corrupt_error_matches() -> None:
    exc = DatabaseError("stmt", {}, Exception("database disk image is malformed"))
    assert _is_sqlite_corrupt_error(exc) is True


def test_extract_sqlite_path(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    extracted = _extract_sqlite_path(url)
    assert extracted == db_path


def test_backup_corrupt_db_moves_file(tmp_path: Path) -> None:
    db_path = tmp_path / "larksync.db"
    db_path.write_text("broken", encoding="utf-8")
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    backup = _backup_corrupt_db(url)
    assert backup is not None
    assert not db_path.exists()
    assert backup.exists()


@pytest.mark.asyncio
async def test_schema_v6_adds_ignored_at_without_changing_existing_problem_state(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "v5-problems.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL NOT NULL
            );
            INSERT INTO sync_meta VALUES ('schema_version', '5', 1);
            CREATE TABLE problems (
                id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                ignored_reason TEXT
            );
            INSERT INTO problems VALUES ('problem-open', 'open', NULL);
            """
        )
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine = await init_db(url)
    async with engine.begin() as conn:
        columns = {
            row[1] for row in (await conn.execute(text("PRAGMA table_info(problems)"))).all()
        }
        row = (
            await conn.execute(
                text("SELECT state, ignored_reason, ignored_at FROM problems WHERE id='problem-open'")
            )
        ).one()
        version = (
            await conn.execute(
                text("SELECT value FROM sync_meta WHERE key='schema_version'")
            )
        ).scalar_one()
    await dispose_engines()

    assert CURRENT_SCHEMA_VERSION == 10
    assert "ignored_at" in columns
    assert (row.state, row.ignored_reason, row.ignored_at) == ("open", None, None)
    assert version == "10"


@pytest.mark.asyncio
async def test_schema_v9_automatically_backs_up_and_scopes_legacy_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "v8-single-account.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL NOT NULL
            );
            INSERT INTO sync_meta VALUES ('schema_version', '8', 1);
            CREATE TABLE sync_tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                local_path TEXT NOT NULL,
                cloud_folder_token TEXT NOT NULL,
                cloud_folder_name TEXT,
                base_path TEXT,
                sync_mode TEXT NOT NULL,
                update_mode TEXT DEFAULT 'auto',
                md_sync_mode TEXT DEFAULT 'enhanced',
                ignored_subpaths TEXT,
                delete_policy TEXT,
                delete_grace_minutes INTEGER,
                owner_device_id TEXT NOT NULL DEFAULT '',
                owner_open_id TEXT,
                is_test INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_run_at REAL
            );
            INSERT INTO sync_tasks (
                id, local_path, cloud_folder_token, sync_mode, created_at, updated_at
            ) VALUES ('task-1', 'D:/Sync', 'fld_1', 'download_only', 1, 1);
            CREATE TABLE sync_links (
                local_path TEXT PRIMARY KEY,
                cloud_token TEXT,
                cloud_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                updated_at REAL NOT NULL DEFAULT 0,
                cloud_parent_token TEXT,
                local_hash TEXT,
                local_size INTEGER,
                local_mtime REAL,
                cloud_revision TEXT,
                cloud_mtime REAL,
                local_resource_signature TEXT,
                resource_sync_revision TEXT,
                placeholder_refresh_revision TEXT
            );
            INSERT INTO sync_links (
                local_path, cloud_token, cloud_type, task_id, updated_at
            ) VALUES ('D:/Sync/a.md', 'doc_1', 'docx', 'task-1', 1);
            """
        )
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine = await init_db(url)
    async with engine.begin() as conn:
        task_account = (
            await conn.execute(text("SELECT account_id FROM sync_tasks WHERE id='task-1'"))
        ).scalar_one()
        link = (
            await conn.execute(
                text("SELECT account_id, local_path FROM sync_links WHERE task_id='task-1'")
            )
        ).one()
        link_pk = {
            row[1]: row[5]
            for row in (await conn.execute(text("PRAGMA table_info(sync_links)"))).all()
        }
        account_count = (await conn.execute(text("SELECT COUNT(*) FROM accounts"))).scalar_one()
        auth_protocol = (
            await conn.execute(
                text("SELECT auth_protocol FROM accounts WHERE id='legacy-default-account'")
            )
        ).scalar_one()
    await dispose_engines()

    backups = list(tmp_path.glob("v8-single-account.db.pre-v10-*.bak"))
    assert len(backups) == 1
    assert task_account == "legacy-default-account"
    assert tuple(link) == ("legacy-default-account", "D:/Sync/a.md")
    assert link_pk["account_id"] == 1
    assert link_pk["local_path"] == 2
    assert account_count == 1
    assert auth_protocol == "legacy_v1"


@pytest.mark.asyncio
async def test_schema_v8_splits_task_check_state_by_direction(tmp_path: Path) -> None:
    db_path = tmp_path / "v7-check-state.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL NOT NULL
            );
            INSERT INTO sync_meta VALUES ('schema_version', '7', 1);
            CREATE TABLE sync_task_check_states (
                task_id TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'idle',
                trigger_source TEXT NOT NULL DEFAULT 'scheduled_download',
                started_at REAL,
                finished_at REAL,
                last_change_at REAL,
                change_count INTEGER NOT NULL DEFAULT 0,
                consecutive_no_change INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                updated_at REAL NOT NULL
            );
            INSERT INTO sync_task_check_states VALUES (
                'task-1', 'no_change', 'scheduled_download', 10, 11, NULL, 0, 5, NULL, 12
            );
            """
        )
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine = await init_db(url)
    async with engine.begin() as conn:
        columns = {
            row[1]: row for row in (await conn.execute(text("PRAGMA table_info(sync_task_check_states)"))).all()
        }
        row = (
            await conn.execute(
                text(
                    "SELECT task_id, direction, trigger_source, consecutive_no_change "
                    "FROM sync_task_check_states WHERE task_id='task-1'"
                )
            )
        ).one()
        await conn.execute(
            text(
                "INSERT INTO sync_task_check_states "
                "(task_id, direction, state, trigger_source, change_count, "
                "consecutive_no_change, updated_at) "
                "VALUES ('task-1', 'upload', 'no_change', 'scheduled_upload', 0, 1, 20)"
            )
        )
        count = (
            await conn.execute(
                text("SELECT COUNT(*) FROM sync_task_check_states WHERE task_id='task-1'")
            )
        ).scalar_one()
    await dispose_engines()

    assert columns["task_id"][5] == 1
    assert columns["direction"][5] == 2
    assert tuple(row) == ("task-1", "download", "scheduled_download", 5)
    assert count == 2


@pytest.mark.asyncio
async def test_sqlite_pragmas_applied(tmp_path: Path) -> None:
    db_path = tmp_path / "larksync.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_engine(url)
    async with engine.begin() as conn:
        journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        busy_timeout = (await conn.execute(text("PRAGMA busy_timeout"))).scalar()
        foreign_keys = (await conn.execute(text("PRAGMA foreign_keys"))).scalar()
    await dispose_engines()
    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 5000
    assert int(foreign_keys) == 1


@pytest.mark.asyncio
async def test_init_db_creates_run_event_and_problem_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "larksync.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = await init_db(url)
    async with engine.begin() as conn:
        tables = {
            row[0]
            for row in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()
        }
        sync_run_indexes = {
            row[1]
            for row in (await conn.execute(text("PRAGMA index_list(sync_runs)"))).all()
        }
        sync_run_event_indexes = {
            row[1]
            for row in (await conn.execute(text("PRAGMA index_list(sync_run_events)"))).all()
        }
    await dispose_engines()
    assert "sync_runs" in tables
    assert "sync_run_events" in tables
    assert "sync_meta" in tables
    assert "problems" in tables
    assert "problem_occurrences" in tables
    assert "problem_actions" in tables
    assert "idx_sync_runs_task_started_updated" in sync_run_indexes
    assert "idx_sync_run_events_run_timestamp" in sync_run_event_indexes
    assert "idx_sync_run_events_task_timestamp" in sync_run_event_indexes
    assert "idx_sync_run_events_run_status_timestamp" in sync_run_event_indexes

    async with engine.begin() as conn:
        problem_indexes = {
            row[1]
            for row in (await conn.execute(text("PRAGMA index_list(problems)"))).all()
        }
        occurrence_indexes = {
            row[1]
            for row in (await conn.execute(text("PRAGMA index_list(problem_occurrences)"))).all()
        }
    assert "idx_problems_state_last_seen" in problem_indexes
    assert "idx_problems_category_state" in problem_indexes
    assert "idx_problem_occurrences_problem_occurred" in occurrence_indexes
    assert "idx_problem_occurrences_source" in occurrence_indexes


@pytest.mark.asyncio
async def test_init_db_records_schema_version(tmp_path: Path) -> None:
    db_path = tmp_path / "larksync.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = await init_db(url)
    async with engine.begin() as conn:
        version = (
            await conn.execute(text("SELECT value FROM sync_meta WHERE key='schema_version'"))
        ).scalar_one()
    await dispose_engines()
    assert version == str(CURRENT_SCHEMA_VERSION)


@pytest.mark.asyncio
async def test_init_db_upgrades_legacy_schema_with_versioned_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as raw_conn:
        raw_conn.executescript(
            """
            CREATE TABLE sync_tasks (
                id TEXT PRIMARY KEY,
                local_path TEXT NOT NULL,
                cloud_folder_token TEXT NOT NULL,
                sync_mode TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE sync_links (
                local_path TEXT PRIMARY KEY,
                cloud_token TEXT,
                cloud_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                updated_at REAL NOT NULL DEFAULT 0
            );
            """
        )
        raw_conn.commit()

    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = await init_db(url)
    async with engine.begin() as conn:
        sync_task_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(sync_tasks)"))).all()
        }
        sync_link_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(sync_links)"))).all()
        }
        sync_run_indexes = {
            row[1]
            for row in (await conn.execute(text("PRAGMA index_list(sync_runs)"))).all()
        }
        version = (
            await conn.execute(text("SELECT value FROM sync_meta WHERE key='schema_version'"))
        ).scalar_one()
    await dispose_engines()

    assert {"update_mode", "ignored_subpaths", "last_run_at"}.issubset(sync_task_columns)
    assert {
        "local_hash",
        "cloud_revision",
        "resource_sync_revision",
        "placeholder_refresh_revision",
    }.issubset(sync_link_columns)
    assert "idx_sync_runs_task_started_updated" in sync_run_indexes
    assert version == str(CURRENT_SCHEMA_VERSION)


@pytest.mark.asyncio
async def test_schema_v4_reclassifies_historical_empty_activity_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "v3-empty-runs.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = await init_db(url)
    service = SyncRunService(session_maker=get_session_maker(url))
    await service.finish_run(
        run_id="historical-empty",
        task_id="task-1",
        trigger_source="scheduled_upload",
        state="success",
        started_at=10.0,
        finished_at=11.0,
        last_event_at=11.0,
        total_files=0,
        completed_files=0,
        failed_files=0,
        skipped_files=0,
        uploaded_files=0,
        downloaded_files=0,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error=None,
        run_kind="activity",
        has_activity=True,
    )
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE sync_meta SET value='3' WHERE key='schema_version'")
        )
    await init_db(url)

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT run_kind, has_activity FROM sync_runs "
                    "WHERE run_id='historical-empty'"
                )
            )
        ).one()
    await dispose_engines()

    assert row.run_kind == "legacy_check"
    assert row.has_activity == 0


@pytest.mark.asyncio
async def test_schema_v5_reclassifies_only_recovered_false_cloud_pending_runs(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "v4-false-pending.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = await init_db(url)
    async with engine.begin() as conn:
        for run_id, path in (
            ("false-pending", "D:/Sync/still-exists.md"),
            ("real-pending", "D:/Sync/really-missing.md"),
        ):
            await conn.execute(
                text(
                    """
                    INSERT INTO sync_runs (
                        run_id, task_id, state, trigger_source, run_kind, has_activity,
                        started_at, total_files, completed_files, failed_files,
                        skipped_files, uploaded_files, downloaded_files, deleted_files,
                        conflict_files, delete_pending_files, delete_failed_files,
                        created_at, updated_at
                    ) VALUES (
                        :run_id, 'task-1', 'success', 'scheduled_download', 'activity', 1,
                        10, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 10, 11
                    )
                    """
                ),
                {"run_id": run_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO sync_run_events (
                        id, task_id, task_name, run_id, timestamp, status, path, created_at
                    ) VALUES (
                        :id, 'task-1', '任务', :run_id, 10, 'delete_pending', :path, 10
                    )
                    """
                ),
                {"id": f"event-{run_id}", "run_id": run_id, "path": path},
            )
        await conn.execute(
            text(
                """
                INSERT INTO sync_tombstones (
                    id, task_id, local_path, source, status, reason, detected_at, expire_at
                ) VALUES (
                    'tombstone-false', 'task-1', 'D:/Sync/still-exists.md',
                    'cloud', 'cancelled', '云端文件已恢复', 10, 10
                )
                """
            )
        )
        await conn.execute(
            text("UPDATE sync_meta SET value='4' WHERE key='schema_version'")
        )
    await init_db(url)

    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT run_id, run_kind, has_activity FROM sync_runs "
                    "ORDER BY run_id"
                )
            )
        ).all()
    await dispose_engines()

    assert [(row.run_id, row.run_kind, row.has_activity) for row in rows] == [
        ("false-pending", "legacy_check", 0),
        ("real-pending", "activity", 1),
    ]
