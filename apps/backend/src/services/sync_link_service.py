from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncLink
from src.db.session import get_session_maker


@dataclass
class SyncLinkItem:
    local_path: str
    cloud_token: str
    cloud_type: str
    task_id: str
    updated_at: float
    cloud_parent_token: str | None = None
    local_hash: str | None = None
    local_size: int | None = None
    local_mtime: float | None = None
    cloud_revision: str | None = None
    cloud_mtime: float | None = None


class SyncLinkService:
    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._session_maker = session_maker

    async def upsert_link(
        self,
        local_path: str,
        cloud_token: str,
        cloud_type: str,
        task_id: str,
        updated_at: float | None = None,
        cloud_parent_token: str | None = None,
        local_hash: str | None = None,
        local_size: int | None = None,
        local_mtime: float | None = None,
        cloud_revision: str | None = None,
        cloud_mtime: float | None = None,
    ) -> SyncLinkItem:
        session_maker = self._session_maker or get_session_maker()
        updated_at = updated_at if updated_at is not None else time.time()
        try:
            async with session_maker() as session:
                record = await session.get(SyncLink, local_path)
                if record:
                    record.cloud_token = cloud_token
                    record.cloud_type = cloud_type
                    record.task_id = task_id
                    record.updated_at = updated_at
                    if cloud_parent_token is not None:
                        record.cloud_parent_token = cloud_parent_token
                    if local_hash is not None:
                        record.local_hash = local_hash
                    if local_size is not None:
                        record.local_size = local_size
                    if local_mtime is not None:
                        record.local_mtime = local_mtime
                    if cloud_revision is not None:
                        record.cloud_revision = cloud_revision
                    if cloud_mtime is not None:
                        record.cloud_mtime = cloud_mtime
                else:
                    session.add(
                        SyncLink(
                            local_path=local_path,
                            cloud_token=cloud_token,
                            cloud_type=cloud_type,
                            task_id=task_id,
                            updated_at=updated_at,
                            cloud_parent_token=cloud_parent_token,
                            local_hash=local_hash,
                            local_size=local_size,
                            local_mtime=local_mtime,
                            cloud_revision=cloud_revision,
                            cloud_mtime=cloud_mtime,
                        )
                    )
                await session.commit()
        except SQLAlchemyError:
            logger.exception("同步映射写入失败，已跳过持久化: {}", local_path)
        return SyncLinkItem(
            local_path=local_path,
            cloud_token=cloud_token,
            cloud_type=cloud_type,
            task_id=task_id,
            updated_at=updated_at,
            cloud_parent_token=cloud_parent_token,
            local_hash=local_hash,
            local_size=local_size,
            local_mtime=local_mtime,
            cloud_revision=cloud_revision,
            cloud_mtime=cloud_mtime,
        )

    async def get_by_local_path(self, local_path: str) -> SyncLinkItem | None:
        session_maker = self._session_maker or get_session_maker()
        try:
            async with session_maker() as session:
                record = await session.get(SyncLink, local_path)
                if not record:
                    return None
                return self._to_item(record)
        except SQLAlchemyError:
            logger.exception("同步映射读取失败，已忽略: {}", local_path)
            return None

    async def list_by_task(self, task_id: str) -> list[SyncLinkItem]:
        session_maker = self._session_maker or get_session_maker()
        try:
            async with session_maker() as session:
                stmt = select(SyncLink).where(SyncLink.task_id == task_id)
                result = await session.execute(stmt)
                return [self._to_item(row) for row in result.scalars().all()]
        except SQLAlchemyError:
            logger.exception("同步映射查询失败，已忽略: task_id={}", task_id)
            return []

    async def list_all(self) -> list[SyncLinkItem]:
        session_maker = self._session_maker or get_session_maker()
        try:
            async with session_maker() as session:
                stmt = select(SyncLink)
                result = await session.execute(stmt)
                return [self._to_item(row) for row in result.scalars().all()]
        except SQLAlchemyError:
            logger.exception("同步映射查询失败，已忽略")
            return []

    async def delete_by_task(self, task_id: str) -> int:
        """删除指定任务的所有同步映射，返回删除数量。"""
        session_maker = self._session_maker or get_session_maker()
        try:
            async with session_maker() as session:
                stmt = delete(SyncLink).where(SyncLink.task_id == task_id)
                result = await session.execute(stmt)
                await session.commit()
                count = result.rowcount or 0  # type: ignore[union-attr]
                logger.info("已清除任务 {} 的 {} 条同步映射", task_id, count)
                return count
        except SQLAlchemyError:
            logger.exception("同步映射删除失败: task_id={}", task_id)
            return 0

    async def delete_by_local_path(self, local_path: str) -> bool:
        session_maker = self._session_maker or get_session_maker()
        try:
            async with session_maker() as session:
                record = await session.get(SyncLink, local_path)
                if not record:
                    return False
                await session.delete(record)
                await session.commit()
                return True
        except SQLAlchemyError:
            logger.exception("同步映射删除失败: {}", local_path)
            return False

    @staticmethod
    def _to_item(record: SyncLink) -> SyncLinkItem:
        return SyncLinkItem(
            local_path=record.local_path,
            cloud_token=record.cloud_token,
            cloud_type=record.cloud_type,
            task_id=record.task_id,
            updated_at=record.updated_at,
            cloud_parent_token=record.cloud_parent_token,
            local_hash=record.local_hash,
            local_size=record.local_size,
            local_mtime=record.local_mtime,
            cloud_revision=record.cloud_revision,
            cloud_mtime=record.cloud_mtime,
        )


__all__ = ["SyncLinkItem", "SyncLinkService"]
