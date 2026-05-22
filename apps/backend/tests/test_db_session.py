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
    init_db,
)


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
async def test_init_db_creates_run_event_tables(tmp_path: Path) -> None:
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
    assert "idx_sync_runs_task_started_updated" in sync_run_indexes
    assert "idx_sync_run_events_run_timestamp" in sync_run_event_indexes
    assert "idx_sync_run_events_task_timestamp" in sync_run_event_indexes
    assert "idx_sync_run_events_run_status_timestamp" in sync_run_event_indexes


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
    assert {"local_hash", "cloud_revision", "resource_sync_revision"}.issubset(sync_link_columns)
    assert "idx_sync_runs_task_started_updated" in sync_run_indexes
    assert version == str(CURRENT_SCHEMA_VERSION)
