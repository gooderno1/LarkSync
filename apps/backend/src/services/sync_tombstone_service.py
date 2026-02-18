from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncTombstone
from src.db.session import get_session_maker


@dataclass
class SyncTombstoneItem:
    id: str
    task_id: str
    local_path: str
    cloud_token: str | None
    cloud_type: str | None
    source: str
    status: str
    reason: str | None
    detected_at: float
    expire_at: float
    executed_at: float | None


class SyncTombstoneService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

    async def create_or_refresh(
        self,
        *,
        task_id: str,
        local_path: str,
        cloud_token: str | None,
        cloud_type: str | None,
        source: str,
        reason: str | None,
        expire_at: float,
    ) -> SyncTombstoneItem:
        now = time.time()
        session_maker = self._session_maker
        try:
            async with session_maker() as session:
                stmt = (
                    select(SyncTombstone)
                    .where(SyncTombstone.task_id == task_id)
                    .where(SyncTombstone.local_path == local_path)
                    .where(SyncTombstone.source == source)
                    .where(SyncTombstone.status == "pending")
                    .order_by(SyncTombstone.detected_at.desc())
                )
                result = await session.execute(stmt)
                record = result.scalars().first()
                if record:
                    record.cloud_token = cloud_token
                    record.cloud_type = cloud_type
                    record.reason = reason
                    # 保留最早检测时间，避免周期刷新导致永远不过期
                    if record.detected_at <= 0:
                        record.detected_at = now
                    if record.expire_at <= 0:
                        record.expire_at = expire_at
                    else:
                        record.expire_at = min(record.expire_at, expire_at)
                else:
                    record = SyncTombstone(
                        id=str(uuid.uuid4()),
                        task_id=task_id,
                        local_path=local_path,
                        cloud_token=cloud_token,
                        cloud_type=cloud_type,
                        source=source,
                        status="pending",
                        reason=reason,
                        detected_at=now,
                        expire_at=expire_at,
                        executed_at=None,
                    )
                    session.add(record)
                await session.commit()
                return self._to_item(record)
        except SQLAlchemyError:
            logger.exception("写入删除墓碑失败: task_id={} path={}", task_id, local_path)
            raise

    async def list_pending(
        self,
        task_id: str,
        *,
        before: float | None = None,
        include_failed: bool = True,
    ) -> list[SyncTombstoneItem]:
        session_maker = self._session_maker
        try:
            async with session_maker() as session:
                statuses = ["pending"]
                if include_failed:
                    statuses.append("failed")
                stmt = (
                    select(SyncTombstone)
                    .where(SyncTombstone.task_id == task_id)
                    .where(SyncTombstone.status.in_(tuple(statuses)))
                    .order_by(SyncTombstone.detected_at.asc())
                )
                if before is not None:
                    stmt = stmt.where(SyncTombstone.expire_at <= before)
                result = await session.execute(stmt)
                return [self._to_item(item) for item in result.scalars().all()]
        except SQLAlchemyError:
            logger.exception("查询删除墓碑失败: task_id={}", task_id)
            return []

    async def mark_status(
        self,
        tombstone_id: str,
        *,
        status: str,
        reason: str | None = None,
        expire_at: float | None = None,
    ) -> bool:
        now = time.time()
        session_maker = self._session_maker
        try:
            async with session_maker() as session:
                record = await session.get(SyncTombstone, tombstone_id)
                if not record:
                    return False
                record.status = status
                if reason is not None:
                    record.reason = reason
                if expire_at is not None:
                    record.expire_at = expire_at
                if status == "executed":
                    record.executed_at = now
                await session.commit()
                return True
        except SQLAlchemyError:
            logger.exception("更新删除墓碑状态失败: id={} status={}", tombstone_id, status)
            return False

    async def delete_by_task(self, task_id: str) -> int:
        session_maker = self._session_maker
        try:
            async with session_maker() as session:
                stmt = delete(SyncTombstone).where(SyncTombstone.task_id == task_id)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount or 0  # type: ignore[union-attr]
        except SQLAlchemyError:
            logger.exception("删除任务墓碑失败: task_id={}", task_id)
            return 0

    @staticmethod
    def _to_item(record: SyncTombstone) -> SyncTombstoneItem:
        return SyncTombstoneItem(
            id=record.id,
            task_id=record.task_id,
            local_path=record.local_path,
            cloud_token=record.cloud_token,
            cloud_type=record.cloud_type,
            source=record.source,
            status=record.status,
            reason=record.reason,
            detected_at=record.detected_at,
            expire_at=record.expire_at,
            executed_at=record.executed_at,
        )


__all__ = ["SyncTombstoneItem", "SyncTombstoneService"]
