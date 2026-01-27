from __future__ import annotations

from typing import Optional

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
    return engine
