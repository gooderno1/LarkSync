from __future__ import annotations

import time

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncMeta, SyncRun
from src.db.session import get_session_maker


_KEY_PREFIX = "sync_schedule_checkpoint_v1"


class SyncScheduleCheckpointService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

    async def get_last_attempt(self, task_id: str, direction: str) -> float | None:
        key = self._key(task_id, direction)
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncMeta, key)
                if record is not None:
                    try:
                        return float(record.value)
                    except (TypeError, ValueError):
                        pass
                trigger_source = f"scheduled_{direction}"
                latest = (
                    await session.execute(
                        select(
                            func.max(
                                func.coalesce(
                                    SyncRun.finished_at,
                                    SyncRun.started_at,
                                )
                            )
                        )
                        .where(SyncRun.task_id == task_id)
                        .where(SyncRun.trigger_source == trigger_source)
                    )
                ).scalar_one_or_none()
                return float(latest) if latest is not None else None
        except SQLAlchemyError:
            logger.exception(
                "读取同步调度检查点失败: task_id={} direction={}",
                task_id,
                direction,
            )
            return None

    async def mark_attempt(
        self,
        task_id: str,
        direction: str,
        attempted_at: float | None = None,
    ) -> None:
        value = time.time() if attempted_at is None else float(attempted_at)
        key = self._key(task_id, direction)
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncMeta, key)
                if record is None:
                    session.add(
                        SyncMeta(
                            key=key,
                            value=str(value),
                            updated_at=value,
                        )
                    )
                else:
                    record.value = str(value)
                    record.updated_at = value
                await session.commit()
        except SQLAlchemyError:
            logger.exception(
                "写入同步调度检查点失败: task_id={} direction={}",
                task_id,
                direction,
            )

    @staticmethod
    def _key(task_id: str, direction: str) -> str:
        if direction not in {"upload", "download"}:
            raise ValueError(f"不支持的同步方向: {direction}")
        return f"{_KEY_PREFIX}:{task_id}:{direction}"


__all__ = ["SyncScheduleCheckpointService"]
