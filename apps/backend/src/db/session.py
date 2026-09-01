from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
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


CURRENT_SCHEMA_VERSION = 12


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
    await _backup_before_schema_upgrade(database_url)
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


async def _apply_schema_v4(conn) -> None:
    await conn.execute(
        text(
            """
            UPDATE sync_runs
            SET has_activity = 0,
                run_kind = 'legacy_check'
            WHERE state = 'success'
              AND last_error IS NULL
              AND uploaded_files = 0
              AND downloaded_files = 0
              AND deleted_files = 0
              AND conflict_files = 0
              AND delete_pending_files = 0
              AND delete_failed_files = 0
              AND failed_files = 0
            """
        )
    )


async def _apply_schema_v5(conn) -> None:
    await conn.execute(
        text(
            """
            UPDATE sync_runs AS run
            SET has_activity = 0,
                run_kind = 'legacy_check'
            WHERE run.state = 'success'
              AND run.last_error IS NULL
              AND run.has_activity = 1
              AND run.trigger_source = 'scheduled_download'
              AND run.uploaded_files = 0
              AND run.downloaded_files = 0
              AND run.deleted_files = 0
              AND run.conflict_files = 0
              AND run.delete_pending_files > 0
              AND run.delete_failed_files = 0
              AND run.failed_files = 0
              AND EXISTS (
                SELECT 1
                FROM sync_run_events AS event
                WHERE event.run_id = run.run_id
                  AND event.status = 'delete_pending'
              )
              AND NOT EXISTS (
                SELECT 1
                FROM sync_run_events AS event
                WHERE event.run_id = run.run_id
                  AND event.status = 'delete_pending'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM sync_tombstones AS tombstone
                    WHERE tombstone.task_id = event.task_id
                      AND tombstone.local_path = event.path
                      AND tombstone.source = 'cloud'
                      AND tombstone.status = 'cancelled'
                      AND tombstone.reason = '云端文件已恢复'
                  )
              )
            """
        )
    )


async def _apply_schema_v6(conn) -> None:
    await _ensure_column(
        conn,
        table="problems",
        column="ignored_at",
        column_type="REAL",
        default_value=None,
    )
    await _ensure_index(
        conn,
        table="problems",
        index_name="idx_problems_state_ignored_at",
        columns_sql="state, ignored_at DESC",
    )


async def _apply_schema_v7(conn) -> None:
    await _ensure_column(
        conn,
        table="sync_links",
        column="placeholder_refresh_revision",
        column_type="TEXT",
        default_value=None,
    )


async def _apply_schema_v8(conn) -> None:
    table_info = list(
        await conn.execute(text("PRAGMA table_info(sync_task_check_states)"))
    )
    columns = {str(row[1]): row for row in table_info}
    has_directional_primary_key = (
        "direction" in columns
        and int(columns["task_id"][5]) == 1
        and int(columns["direction"][5]) == 2
    )
    if has_directional_primary_key:
        await _ensure_index(
            conn,
            table="sync_task_check_states",
            index_name="ix_sync_task_check_states_state",
            columns_sql="state",
        )
        return

    await conn.execute(text("DROP TABLE IF EXISTS sync_task_check_states_v8"))
    await conn.execute(
        text(
            """
            CREATE TABLE sync_task_check_states_v8 (
                task_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'idle',
                trigger_source TEXT NOT NULL DEFAULT 'scheduled_download',
                started_at REAL,
                finished_at REAL,
                last_change_at REAL,
                change_count INTEGER NOT NULL DEFAULT 0,
                consecutive_no_change INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                updated_at REAL NOT NULL,
                PRIMARY KEY (task_id, direction)
            )
            """
        )
    )
    if table_info:
        direction_sql = (
            "COALESCE(NULLIF(direction, ''), "
            "CASE WHEN lower(trigger_source) LIKE '%download%' "
            "THEN 'download' ELSE 'upload' END)"
            if "direction" in columns
            else (
                "CASE WHEN lower(trigger_source) LIKE '%download%' "
                "THEN 'download' ELSE 'upload' END"
            )
        )
        await conn.execute(
            text(
                f"""
                INSERT OR REPLACE INTO sync_task_check_states_v8 (
                    task_id, direction, state, trigger_source, started_at,
                    finished_at, last_change_at, change_count,
                    consecutive_no_change, last_error, updated_at
                )
                SELECT task_id, {direction_sql}, state, trigger_source, started_at,
                       finished_at, last_change_at, change_count,
                       consecutive_no_change, last_error, updated_at
                FROM sync_task_check_states
                """
            )
        )
        await conn.execute(text("DROP TABLE sync_task_check_states"))
    await conn.execute(
        text("ALTER TABLE sync_task_check_states_v8 RENAME TO sync_task_check_states")
    )
    await _ensure_index(
        conn,
        table="sync_task_check_states",
        index_name="ix_sync_task_check_states_state",
        columns_sql="state",
    )


async def _apply_schema_v9(conn) -> None:
    legacy_account_id = "legacy-default-account"
    now = datetime.now().timestamp()
    has_legacy_data = (
        await conn.execute(text("SELECT 1 FROM sync_tasks LIMIT 1"))
    ).first()
    if has_legacy_data:
        await conn.execute(
        text(
            """
            INSERT OR IGNORE INTO app_profiles (
                id, brand, app_id, display_name, source, secret_ref,
                enabled, created_at, updated_at
            ) VALUES (
                'legacy-default-app', 'feishu', 'legacy-config',
                '升级迁移的应用配置', 'legacy', 'legacy-config', 1,
                :now, :now
            )
            """
        ),
        {"now": now},
        )
        await conn.execute(
        text(
            """
            INSERT OR IGNORE INTO accounts (
                id, app_profile_id, brand, open_id, account_name,
                state, granted_scopes, paused, created_at, updated_at
            ) VALUES (
                :account_id, 'legacy-default-app', 'feishu',
                'legacy-pending', '原有飞书账号', 'migration_pending',
                '[]', 0, :now, :now
            )
            """
        ),
        {"account_id": legacy_account_id, "now": now},
        )

    scoped_tables = (
        "sync_tasks",
        "sync_tombstones",
        "conflicts",
        "sync_runs",
        "sync_task_check_states",
        "sync_run_events",
        "problems",
        "problem_recovery_facts",
        "problem_occurrences",
        "problem_actions",
        "sync_block_states",
    )
    for table in scoped_tables:
        await _ensure_column(
            conn,
            table=table,
            column="account_id",
            column_type="TEXT",
            default_value=legacy_account_id,
        )
        await conn.execute(
            text(
                f"UPDATE {table} SET account_id=:account_id "
                "WHERE account_id IS NULL OR account_id=''"
            ),
            {"account_id": legacy_account_id},
        )
        await _ensure_index(
            conn,
            table=table,
            index_name=f"idx_{table}_account_id",
            columns_sql="account_id",
        )

    await _rebuild_sync_links_v9(conn, legacy_account_id=legacy_account_id)
    await _rebuild_sync_mappings_v9(conn, legacy_account_id=legacy_account_id)
    if has_legacy_data:
        await conn.execute(
            text(
                """
                INSERT INTO ui_preferences (device_id, active_account_id, updated_at)
                VALUES ('legacy-device', :account_id, :now)
                ON CONFLICT(device_id) DO UPDATE SET
                    active_account_id=COALESCE(ui_preferences.active_account_id, excluded.active_account_id),
                    updated_at=excluded.updated_at
                """
            ),
            {"account_id": legacy_account_id, "now": now},
        )


async def _apply_schema_v10(conn) -> None:
    await _ensure_column(
        conn,
        table="accounts",
        column="auth_protocol",
        column_type="TEXT",
        default_value="device_v2",
    )
    await conn.execute(
        text(
            "UPDATE accounts SET auth_protocol='legacy_v1' "
            "WHERE id='legacy-default-account'"
        )
    )
    await _ensure_index(
        conn,
        table="accounts",
        index_name="idx_accounts_auth_protocol",
        columns_sql="auth_protocol",
    )


async def _apply_schema_v11(conn) -> None:
    fields = (
        ("tenant_key", "TEXT", None),
        ("tenant_display_id", "TEXT", None),
        ("tenant_tag", "INTEGER", None),
        ("tenant_avatar_url", "TEXT", None),
        ("tenant_avatar_cache_path", "TEXT", None),
        ("tenant_metadata_status", "TEXT", None),
        ("tenant_metadata_updated_at", "REAL", None),
        ("account_alias", "TEXT", None),
    )
    for column, column_type, default_value in fields:
        await _ensure_column(
            conn,
            table="accounts",
            column=column,
            column_type=column_type,
            default_value=default_value,
        )
    await _ensure_index(
        conn,
        table="accounts",
        index_name="idx_accounts_tenant_key",
        columns_sql="tenant_key",
    )


async def _apply_schema_v12(conn) -> None:
    """保存组织权限诊断，支持升级后继续扫码开通并自动复检。"""
    for column, column_type in (
        ("tenant_metadata_error_code", "TEXT"),
        ("tenant_permission_url", "TEXT"),
    ):
        await _ensure_column(
            conn,
            table="accounts",
            column=column,
            column_type=column_type,
            default_value=None,
        )


async def _rebuild_sync_links_v9(conn, *, legacy_account_id: str) -> None:
    table_info = list(await conn.execute(text("PRAGMA table_info(sync_links)")))
    columns = {str(row[1]): row for row in table_info}
    if (
        "account_id" in columns
        and int(columns["account_id"][5]) == 1
        and int(columns["local_path"][5]) == 2
    ):
        return
    await conn.execute(text("DROP TABLE IF EXISTS sync_links_v9"))
    await conn.execute(
        text(
            """
            CREATE TABLE sync_links_v9 (
                account_id TEXT NOT NULL,
                local_path TEXT NOT NULL,
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
                placeholder_refresh_revision TEXT,
                PRIMARY KEY (account_id, local_path)
            )
            """
        )
    )
    if table_info:
        account_sql = (
            "COALESCE(NULLIF(account_id, ''), :account_id)"
            if "account_id" in columns
            else ":account_id"
        )
        await conn.execute(
            text(
                f"""
                INSERT OR REPLACE INTO sync_links_v9 (
                    account_id, local_path, cloud_token, cloud_type, task_id,
                    updated_at, cloud_parent_token, local_hash, local_size,
                    local_mtime, cloud_revision, cloud_mtime,
                    local_resource_signature, resource_sync_revision,
                    placeholder_refresh_revision
                )
                SELECT {account_sql}, local_path, cloud_token, cloud_type, task_id,
                       updated_at, cloud_parent_token, local_hash, local_size,
                       local_mtime, cloud_revision, cloud_mtime,
                       local_resource_signature, resource_sync_revision,
                       placeholder_refresh_revision
                FROM sync_links
                """
            ),
            {"account_id": legacy_account_id},
        )
        await conn.execute(text("DROP TABLE sync_links"))
    await conn.execute(text("ALTER TABLE sync_links_v9 RENAME TO sync_links"))
    await _ensure_index(
        conn,
        table="sync_links",
        index_name="idx_sync_links_account_id",
        columns_sql="account_id",
    )
    await _ensure_index(
        conn,
        table="sync_links",
        index_name="ix_sync_links_cloud_token",
        columns_sql="cloud_token",
    )
    await _ensure_index(
        conn,
        table="sync_links",
        index_name="ix_sync_links_task_id",
        columns_sql="task_id",
    )


async def _rebuild_sync_mappings_v9(conn, *, legacy_account_id: str) -> None:
    table_info = list(await conn.execute(text("PRAGMA table_info(sync_mappings)")))
    columns = {str(row[1]): row for row in table_info}
    if (
        "account_id" in columns
        and int(columns["account_id"][5]) == 1
        and int(columns["file_hash"][5]) == 2
    ):
        return
    await conn.execute(text("DROP TABLE IF EXISTS sync_mappings_v9"))
    await conn.execute(
        text(
            """
            CREATE TABLE sync_mappings_v9 (
                account_id TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                feishu_token TEXT,
                local_path TEXT NOT NULL,
                last_sync_mtime REAL NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (account_id, file_hash)
            )
            """
        )
    )
    if table_info:
        await conn.execute(
            text(
                """
                INSERT INTO sync_mappings_v9 (
                    account_id, file_hash, feishu_token, local_path,
                    last_sync_mtime, version
                )
                SELECT :account_id, file_hash, feishu_token, local_path,
                       last_sync_mtime, version
                FROM sync_mappings
                """
            ),
            {"account_id": legacy_account_id},
        )
        await conn.execute(text("DROP TABLE sync_mappings"))
    await conn.execute(
        text("ALTER TABLE sync_mappings_v9 RENAME TO sync_mappings")
    )
    await _ensure_index(
        conn,
        table="sync_mappings",
        index_name="idx_sync_mappings_account_id",
        columns_sql="account_id",
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
    SchemaMigration(
        version=4,
        description="重新分类被误标为活动的历史空运行",
        upgrade=_apply_schema_v4,
    ),
    SchemaMigration(
        version=5,
        description="归档云端对象仍存在造成的历史虚假待删运行",
        upgrade=_apply_schema_v5,
    ),
    SchemaMigration(
        version=6,
        description="补齐问题人工忽略时间与状态查询索引",
        upgrade=_apply_schema_v6,
    ),
    SchemaMigration(
        version=7,
        description="记录 Docx 占位符回刷版本，避免同一云端版本无限重转",
        upgrade=_apply_schema_v7,
    ),
    SchemaMigration(
        version=8,
        description="按同步方向独立保存任务检测结果，避免上传检测覆盖下载恢复事实",
        upgrade=_apply_schema_v8,
    ),
    SchemaMigration(
        version=9,
        description="自动备份并升级为账号级数据隔离、复合同步映射和通知模型",
        upgrade=_apply_schema_v9,
    ),
    SchemaMigration(
        version=10,
        description="记录账号 OAuth 协议，兼容迁移账号 V1 刷新并支持 Device Flow V2",
        upgrade=_apply_schema_v10,
    ),
    SchemaMigration(
        version=11,
        description="补充账号组织标识、组织头像和本地组织别名",
        upgrade=_apply_schema_v11,
    ),
    SchemaMigration(
        version=12,
        description="记录组织权限错误码和官方权限开通入口",
        upgrade=_apply_schema_v12,
    ),
]


async def _backup_before_schema_upgrade(database_url: Optional[str]) -> Optional[Path]:
    db_path = _extract_sqlite_path(database_url)
    if db_path is None or not db_path.exists() or not db_path.is_file():
        return None

    def _backup() -> Optional[Path]:
        try:
            with sqlite3.connect(db_path) as source:
                row = source.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_meta'"
                ).fetchone()
                version = 0
                if row:
                    version_row = source.execute(
                        "SELECT value FROM sync_meta WHERE key='schema_version'"
                    ).fetchone()
                    if version_row:
                        try:
                            version = int(version_row[0])
                        except (TypeError, ValueError):
                            version = 0
                if version >= CURRENT_SCHEMA_VERSION:
                    return None
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup_path = db_path.with_name(
                    f"{db_path.name}.pre-v{CURRENT_SCHEMA_VERSION}-{timestamp}.bak"
                )
                with sqlite3.connect(backup_path) as destination:
                    source.backup(destination)
                return backup_path
        except sqlite3.DatabaseError:
            return None

    import asyncio

    backup_path = await asyncio.to_thread(_backup)
    if backup_path:
        logger.info("数据库升级前自动备份完成: {}", backup_path)
    return backup_path


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
