from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from src.db.session import (
    _backup_corrupt_db,
    _extract_sqlite_path,
    _is_sqlite_corrupt_error,
    _sqlite_literal,
    create_engine,
    dispose_engines,
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
