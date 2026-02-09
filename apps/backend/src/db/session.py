from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import ConfigManager

from .base import Base


_ENGINE_CACHE: dict[str, AsyncEngine] = {}


def create_engine(database_url: Optional[str] = None) -> AsyncEngine:
    if database_url is None:
        database_url = ConfigManager.get().config.database_url
    cached = _ENGINE_CACHE.get(database_url)
    if cached is not None:
        return cached
    engine = create_async_engine(database_url, future=True)
    _configure_sqlite_engine(engine, database_url)
    _ENGINE_CACHE[database_url] = engine
    return engine


def get_session_maker(database_url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(database_url: Optional[str] = None) -> AsyncEngine:
    engine = create_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_column(
                conn,
                table="sync_tasks",
                column="update_mode",
                column_type="TEXT",
                default_value="auto",
            )
            await _ensure_column(
                conn,
                table="sync_tasks",
                column="cloud_folder_name",
                column_type="TEXT",
                default_value=None,
            )
            await _ensure_column(
                conn,
                table="sync_links",
                column="cloud_parent_token",
                column_type="TEXT",
                default_value=None,
            )
        return engine
    except DatabaseError as exc:
        if not _is_sqlite_corrupt_error(exc):
            raise
        logger.error("检测到数据库损坏，尝试备份并重建: {}", exc)
        await engine.dispose()
        backup = _backup_corrupt_db(database_url)
        if backup:
            logger.warning("已备份损坏数据库到: {}", backup)
        engine = create_engine(database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_column(
                conn,
                table="sync_tasks",
                column="update_mode",
                column_type="TEXT",
                default_value="auto",
            )
            await _ensure_column(
                conn,
                table="sync_tasks",
                column="cloud_folder_name",
                column_type="TEXT",
                default_value=None,
            )
            await _ensure_column(
                conn,
                table="sync_links",
                column="cloud_parent_token",
                column_type="TEXT",
                default_value=None,
            )
        return engine


async def dispose_engines() -> None:
    for url, engine in list(_ENGINE_CACHE.items()):
        try:
            await engine.dispose()
        except Exception as exc:
            logger.warning("释放数据库连接失败 ({}): {}", url, exc)
        finally:
            _ENGINE_CACHE.pop(url, None)


async def _ensure_column(
    conn,
    *,
    table: str,
    column: str,
    column_type: str,
    default_value: Union[str, int, float, bool, None],
) -> None:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    columns = {row[1] for row in result}
    if column in columns:
        return
    default_literal = _sqlite_literal(default_value)
    await conn.execute(
        text(
            f"ALTER TABLE {table} ADD COLUMN {column} {column_type} DEFAULT {default_literal}"
        )
    )


def _sqlite_literal(value: Union[str, int, float, bool, None]) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _is_sqlite_corrupt_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return (
        "database disk image is malformed" in message
        or "file is not a database" in message
    )


def _is_sqlite_url(database_url: Optional[str]) -> bool:
    if not database_url:
        return False
    try:
        url = make_url(database_url)
    except Exception:
        return False
    return url.get_backend_name() == "sqlite"


def _configure_sqlite_engine(engine: AsyncEngine, database_url: Optional[str]) -> None:
    if not _is_sqlite_url(database_url):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        except Exception as exc:
            logger.warning("SQLite PRAGMA 初始化失败: {}", exc)
        finally:
            cursor.close()


def _extract_sqlite_path(database_url: Optional[str]) -> Optional[Path]:
    if not database_url:
        database_url = ConfigManager.get().config.database_url
    try:
        url = make_url(database_url)
    except Exception:
        return None
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database:
        return None
    return Path(url.database)


def _backup_corrupt_db(database_url: Optional[str]) -> Optional[Path]:
    db_path = _extract_sqlite_path(database_url)
    if not db_path:
        return None
    if not db_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_suffix(f"{db_path.suffix}.corrupt-{timestamp}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        db_path.replace(backup_path)
    except OSError:
        return None
    return backup_path


__all__ = [
    "create_engine",
    "get_session_maker",
    "init_db",
    "dispose_engines",
    "_backup_corrupt_db",
    "_extract_sqlite_path",
    "_is_sqlite_corrupt_error",
    "_is_sqlite_url",
    "_configure_sqlite_engine",
    "_sqlite_literal",
]
