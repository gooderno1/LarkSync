from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncTaskCheckState
from src.db.session import get_session_maker


@dataclass(frozen=True)
class SyncTaskCheckStateItem:
    task_id: str
    state: str
    trigger_source: str
    started_at: float | None
    finished_at: float | None
    last_change_at: float | None
    change_count: int
    consecutive_no_change: int
    last_error: str | None
    updated_at: float


class SyncTaskCheckStateService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

    async def mark_started(
        self,
        *,
        task_id: str,
        trigger_source: str,
        started_at: float,
    ) -> SyncTaskCheckStateItem | None:
        return await self._upsert(
            task_id=task_id,
            state="checking",
            trigger_source=trigger_source,
            started_at=started_at,
            finished_at=None,
            change_count=0,
            last_error=None,
        )

    async def mark_finished(
        self,
        *,
        task_id: str,
        trigger_source: str,
        started_at: float | None,
        finished_at: float,
        change_count: int,
        last_error: str | None = None,
    ) -> SyncTaskCheckStateItem | None:
        if last_error and change_count <= 0:
            state = "failed"
        elif change_count > 0:
            state = "changes_found"
        else:
            state = "no_change"
        return await self._upsert(
            task_id=task_id,
            state=state,
            trigger_source=trigger_source,
            started_at=started_at,
            finished_at=finished_at,
            change_count=max(0, change_count),
            last_error=last_error,
        )

    async def get_many(self, task_ids: list[str]) -> dict[str, SyncTaskCheckStateItem]:
        if not task_ids:
            return {}
        try:
            async with self._session_maker() as session:
                rows = await session.execute(
                    select(SyncTaskCheckState).where(SyncTaskCheckState.task_id.in_(task_ids))
                )
                return {item.task_id: self._to_item(item) for item in rows.scalars().all()}
        except SQLAlchemyError:
            logger.exception("读取任务检测状态失败")
            return {}

    async def _upsert(
        self,
        *,
        task_id: str,
        state: str,
        trigger_source: str,
        started_at: float | None,
        finished_at: float | None,
        change_count: int,
        last_error: str | None,
    ) -> SyncTaskCheckStateItem | None:
        now = time.time()
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncTaskCheckState, task_id)
                if record is None:
                    record = SyncTaskCheckState(
                        task_id=task_id,
                        state=state,
                        trigger_source=trigger_source,
                        started_at=started_at,
                        finished_at=finished_at,
                        last_change_at=finished_at if change_count > 0 else None,
                        change_count=change_count,
                        consecutive_no_change=1 if state == "no_change" else 0,
                        last_error=last_error,
                        updated_at=now,
                    )
                    session.add(record)
                else:
                    record.state = state
                    record.trigger_source = trigger_source
                    record.started_at = started_at
                    record.finished_at = finished_at
                    record.change_count = change_count
                    record.last_error = last_error
                    record.updated_at = now
                    if state == "no_change":
                        record.consecutive_no_change += 1
                    elif state != "checking":
                        record.consecutive_no_change = 0
                    if change_count > 0 and finished_at is not None:
                        record.last_change_at = finished_at
                await session.commit()
                await session.refresh(record)
                return self._to_item(record)
        except SQLAlchemyError:
            logger.exception("更新任务检测状态失败: task_id={}", task_id)
            return None

    @staticmethod
    def _to_item(record: SyncTaskCheckState) -> SyncTaskCheckStateItem:
        return SyncTaskCheckStateItem(
            task_id=record.task_id,
            state=record.state,
            trigger_source=record.trigger_source,
            started_at=record.started_at,
            finished_at=record.finished_at,
            last_change_at=record.last_change_at,
            change_count=record.change_count,
            consecutive_no_change=record.consecutive_no_change,
            last_error=record.last_error,
            updated_at=record.updated_at,
        )


__all__ = ["SyncTaskCheckStateItem", "SyncTaskCheckStateService"]
