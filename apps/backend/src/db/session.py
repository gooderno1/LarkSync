from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional, Union

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import ConfigManager
from .base import Base
from . import models as _models  # noqa: F401  # 确保所有 ORM 模型在 create_all 前完成注册


_ENGINE_CACHE: dict[str, AsyncEngine] = {}
SCHEMA_VERSION_KEY = "schema_version"


MigrationFn = Callable[[object], Awaitable[None]]


@dataclass(frozen=True)
class SchemaMigration:
    version: int
    description: str
    upgrade: MigrationFn


CURRENT_SCHEMA_VERSION = 3


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
            await _run_schema_migrations(conn)
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
            await _run_schema_migrations(conn)
        return engine


async def dispose_engines() -> None:
    for url, engine in list(_ENGINE_CACHE.items()):
        try:
            await engine.dispose()
        except Exception as exc:
            logger.warning("释放数据库连接失败 ({}): {}", url, exc)
        finally:
            _ENGINE_CACHE.pop(url, None)


async def _run_schema_migrations(conn) -> None:
    current_version = await _read_schema_version(conn)
    for migration in _SCHEMA_MIGRATIONS:
        if migration.version <= current_version:
            continue
        logger.info("执行数据库迁移 v{}: {}", migration.version, migration.description)
        await migration.upgrade(conn)
        await _set_schema_version(conn, migration.version)
        current_version = migration.version


async def _read_schema_version(conn) -> int:
    meta_exists = (
        await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_meta'"
            )
        )
    ).first()
    if not meta_exists:
        return 0
    value = (
        await conn.execute(
            text("SELECT value FROM sync_meta WHERE key = :key"),
            {"key": SCHEMA_VERSION_KEY},
        )
    ).scalar_one_or_none()
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


async def _set_schema_version(conn, version: int) -> None:
    timestamp = datetime.now().timestamp()
    await conn.execute(
        text(
            """
            INSERT INTO sync_meta (key, value, updated_at)
            VALUES (:key, :value, :updated_at)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """
        ),
        {
            "key": SCHEMA_VERSION_KEY,
            "value": str(version),
            "updated_at": timestamp,
        },
    )


async def _apply_schema_v1(conn) -> None:
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
        column="md_sync_mode",
        column_type="TEXT",
        default_value="enhanced",
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="ignored_subpaths",
        column_type="TEXT",
        default_value=None,
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
        table="sync_tasks",
        column="owner_device_id",
        column_type="TEXT",
        default_value="",
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="owner_open_id",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="is_test",
        column_type="INTEGER",
        default_value=False,
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="delete_policy",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="delete_grace_minutes",
        column_type="INTEGER",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_tasks",
        column="last_run_at",
        column_type="REAL",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="cloud_parent_token",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="local_hash",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="local_size",
        column_type="INTEGER",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="local_mtime",
        column_type="REAL",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="cloud_revision",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="cloud_mtime",
        column_type="REAL",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="local_resource_signature",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_column(
        conn,
        table="sync_links",
        column="resource_sync_revision",
        column_type="TEXT",
        default_value=None,
    )
    await _ensure_index(
        conn,
        table="sync_runs",
        index_name="idx_sync_runs_task_started_updated",
        columns_sql="task_id, started_at DESC, updated_at DESC",
    )
    await _ensure_index(
        conn,
        table="sync_run_events",
        index_name="idx_sync_run_events_run_timestamp",
        columns_sql="run_id, timestamp DESC",
    )
    await _ensure_index(
        conn,
        table="sync_run_events",
        index_name="idx_sync_run_events_task_timestamp",
        columns_sql="task_id, timestamp DESC",
    )
    await _ensure_index(
        conn,
        table="sync_run_events",
        index_name="idx_sync_run_events_run_status_timestamp",
        columns_sql="run_id, status, timestamp DESC",
    )


async def _apply_schema_v2(conn) -> None:
    await _ensure_index(
        conn,
        table="problems",
        index_name="idx_problems_state_last_seen",
        columns_sql="state, last_seen_at DESC",
    )
    await _ensure_index(
        conn,
        table="problems",
        index_name="idx_problems_category_state",
        columns_sql="category, state",
    )
    await _ensure_index(
        conn,
        table="problems",
        index_name="idx_problems_task_state",
        columns_sql="task_id, state",
    )
    await _ensure_index(
        conn,
        table="problem_occurrences",
        index_name="idx_problem_occurrences_problem_occurred",
        columns_sql="problem_id, occurred_at DESC",
    )
    await _ensure_index(
        conn,
        table="problem_occurrences",
        index_name="idx_problem_occurrences_source",
        columns_sql="source_kind, source_id",
        unique=True,
    )
    await _ensure_index(
        conn,
        table="problem_actions",
        index_name="idx_problem_actions_problem_requested",
        columns_sql="problem_id, requested_at DESC",
    )


async def _apply_schema_v3(conn) -> None:
    await _ensure_column(
        conn,
        table="sync_runs",
        column="run_kind",
        column_type="TEXT",
        default_value="activity",
    )
    await _ensure_column(
        conn,
        table="sync_runs",
        column="has_activity",
        column_type="INTEGER",
        default_value=True,
    )
    for column, column_type, default_value in (
        ("resolution_key", "TEXT", None),
        ("operation_family", "TEXT", None),
        ("actionability", "TEXT", "diagnostic_only"),
        ("resolved_by_run_id", "TEXT", None),
        ("resolved_by_event_id", "TEXT", None),
        ("last_good_at", "REAL", None),
    ):
        await _ensure_column(
            conn,
            table="problems",
            column=column,
            column_type=column_type,
            default_value=default_value,
        )
    await conn.execute(
        text(
            """
            UPDATE sync_runs
            SET has_activity = CASE
                  WHEN state IN ('failed', 'cancelled') OR last_error IS NOT NULL THEN 1
                  WHEN uploaded_files + downloaded_files + deleted_files + conflict_files
                       + delete_pending_files + delete_failed_files + failed_files > 0 THEN 1
                  ELSE 0
                END,
                run_kind = CASE
                  WHEN state IN ('failed', 'cancelled') OR last_error IS NOT NULL THEN 'activity'
                  WHEN uploaded_files + downloaded_files + deleted_files + conflict_files
                       + delete_pending_files + delete_failed_files + failed_files > 0 THEN 'activity'
                  ELSE 'legacy_check'
                END
            """
        )
    )
    await _ensure_index(
        conn,
        table="sync_runs",
        index_name="idx_sync_runs_task_activity_started",
        columns_sql="task_id, has_activity, started_at DESC",
    )
    await _ensure_index(
        conn,
        table="problems",
        index_name="idx_problems_resolution_state",
        columns_sql="resolution_key, state, last_seen_at",
    )


_SCHEMA_MIGRATIONS = [
    SchemaMigration(
        version=1,
        description="补齐 sync_tasks/sync_links 历史列，并创建 sync_runs/sync_run_events 复合索引",
        upgrade=_apply_schema_v1,
    ),
    SchemaMigration(
        version=2,
        description="新增统一问题、出现记录和动作记录索引",
        upgrade=_apply_schema_v2,
    ),
    SchemaMigration(
        version=3,
        description="区分检测与活动运行，并增加问题恢复事实和自动结案字段",
        upgrade=_apply_schema_v3,
    ),
]


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


async def _ensure_index(
    conn,
    *,
    table: str,
    index_name: str,
    columns_sql: str,
    unique: bool = False,
) -> None:
    result = await conn.execute(text(f"PRAGMA index_list({table})"))
    indexes = {str(row[1]) for row in result}
    if index_name in indexes:
        return
    qualifier = "UNIQUE " if unique else ""
    await conn.execute(
        text(f"CREATE {qualifier}INDEX IF NOT EXISTS {index_name} ON {table} ({columns_sql})")
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
    "CURRENT_SCHEMA_VERSION",
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
