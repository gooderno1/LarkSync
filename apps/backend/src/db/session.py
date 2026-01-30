from __future__ import annotations

from typing import Optional, Union

from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import ConfigManager

from .base import Base


def create_engine(database_url: Optional[str] = None) -> AsyncEngine:
    if database_url is None:
        database_url = ConfigManager.get().config.database_url
    return create_async_engine(database_url, future=True)


def get_session_maker(database_url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(database_url: Optional[str] = None) -> AsyncEngine:
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
    return engine


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


__all__ = [
    "create_engine",
    "get_session_maker",
    "init_db",
]
