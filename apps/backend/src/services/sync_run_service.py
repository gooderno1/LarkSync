from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncRun
from src.db.session import get_session_maker


@dataclass
class SyncRunItem:
    run_id: str
    task_id: str
    state: str
    trigger_source: str
    started_at: float
    finished_at: float | None
    last_event_at: float | None
    total_files: int
    completed_files: int
    failed_files: int
    skipped_files: int
    uploaded_files: int
    downloaded_files: int
    deleted_files: int
    conflict_files: int
    delete_pending_files: int
    delete_failed_files: int
    last_error: str | None
    created_at: float
    updated_at: float


class SyncRunService:
    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

    async def start_run(
        self,
        *,
        run_id: str,
        task_id: str,
        trigger_source: str,
        started_at: float,
    ) -> SyncRunItem:
        now = time.time()
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncRun, run_id)
                if record is None:
                    record = SyncRun(
                        run_id=run_id,
                        task_id=task_id,
                        state="running",
                        trigger_source=trigger_source,
                        started_at=started_at,
                        finished_at=None,
                        last_event_at=started_at,
                        total_files=0,
                        completed_files=0,
                        failed_files=0,
                        skipped_files=0,
                        uploaded_files=0,
                        downloaded_files=0,
                        deleted_files=0,
                        conflict_files=0,
                        delete_pending_files=0,
                        delete_failed_files=0,
                        last_error=None,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(record)
                else:
                    record.task_id = task_id
                    record.state = "running"
                    record.trigger_source = trigger_source
                    record.started_at = started_at
                    record.finished_at = None
                    record.last_event_at = started_at
                    record.total_files = 0
                    record.completed_files = 0
                    record.failed_files = 0
                    record.skipped_files = 0
                    record.uploaded_files = 0
                    record.downloaded_files = 0
                    record.deleted_files = 0
                    record.conflict_files = 0
                    record.delete_pending_files = 0
                    record.delete_failed_files = 0
                    record.last_error = None
                    record.updated_at = now
                await session.commit()
                await session.refresh(record)
                return self._to_item(record)
        except SQLAlchemyError:
            logger.exception("运行摘要写入失败(start): task_id={} run_id={}", task_id, run_id)
            return SyncRunItem(
                run_id=run_id,
                task_id=task_id,
                state="running",
                trigger_source=trigger_source,
                started_at=started_at,
                finished_at=None,
                last_event_at=started_at,
                total_files=0,
                completed_files=0,
                failed_files=0,
                skipped_files=0,
                uploaded_files=0,
                downloaded_files=0,
                deleted_files=0,
                conflict_files=0,
                delete_pending_files=0,
                delete_failed_files=0,
                last_error=None,
                created_at=now,
                updated_at=now,
            )

    async def finish_run(
        self,
        *,
        run_id: str,
        task_id: str,
        trigger_source: str,
        state: str,
        started_at: float | None,
        finished_at: float | None,
        last_event_at: float | None,
        total_files: int,
        completed_files: int,
        failed_files: int,
        skipped_files: int,
        uploaded_files: int,
        downloaded_files: int,
        deleted_files: int,
        conflict_files: int,
        delete_pending_files: int,
        delete_failed_files: int,
        last_error: str | None,
    ) -> SyncRunItem:
        now = time.time()
        safe_started_at = started_at if started_at is not None else now
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncRun, run_id)
                if record is None:
                    record = SyncRun(
                        run_id=run_id,
                        task_id=task_id,
                        state=state,
                        trigger_source=trigger_source,
                        started_at=safe_started_at,
                        finished_at=finished_at,
                        last_event_at=last_event_at or finished_at or safe_started_at,
                        total_files=total_files,
                        completed_files=completed_files,
                        failed_files=failed_files,
                        skipped_files=skipped_files,
                        uploaded_files=uploaded_files,
                        downloaded_files=downloaded_files,
                        deleted_files=deleted_files,
                        conflict_files=conflict_files,
                        delete_pending_files=delete_pending_files,
                        delete_failed_files=delete_failed_files,
                        last_error=last_error,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(record)
                else:
                    record.task_id = task_id
                    record.state = state
                    record.trigger_source = trigger_source
                    record.started_at = safe_started_at
                    record.finished_at = finished_at
                    record.last_event_at = last_event_at or finished_at or safe_started_at
                    record.total_files = total_files
                    record.completed_files = completed_files
                    record.failed_files = failed_files
                    record.skipped_files = skipped_files
                    record.uploaded_files = uploaded_files
                    record.downloaded_files = downloaded_files
                    record.deleted_files = deleted_files
                    record.conflict_files = conflict_files
                    record.delete_pending_files = delete_pending_files
                    record.delete_failed_files = delete_failed_files
                    record.last_error = last_error
                    record.updated_at = now
                await session.commit()
                await session.refresh(record)
                return self._to_item(record)
        except SQLAlchemyError:
            logger.exception("运行摘要写入失败(finish): task_id={} run_id={}", task_id, run_id)
            return SyncRunItem(
                run_id=run_id,
                task_id=task_id,
                state=state,
                trigger_source=trigger_source,
                started_at=safe_started_at,
                finished_at=finished_at,
                last_event_at=last_event_at or finished_at or safe_started_at,
                total_files=total_files,
                completed_files=completed_files,
                failed_files=failed_files,
                skipped_files=skipped_files,
                uploaded_files=uploaded_files,
                downloaded_files=downloaded_files,
                deleted_files=deleted_files,
                conflict_files=conflict_files,
                delete_pending_files=delete_pending_files,
                delete_failed_files=delete_failed_files,
                last_error=last_error,
                created_at=now,
                updated_at=now,
            )

    async def get_run(self, run_id: str) -> SyncRunItem | None:
        try:
            async with self._session_maker() as session:
                record = await session.get(SyncRun, run_id)
                return self._to_item(record) if record else None
        except SQLAlchemyError:
            logger.exception("运行摘要读取失败: run_id={}", run_id)
            return None

    async def list_by_task(self, task_id: str, *, limit: int = 50) -> list[SyncRunItem]:
        stmt = (
            select(SyncRun)
            .where(SyncRun.task_id == task_id)
            .order_by(SyncRun.started_at.desc(), SyncRun.updated_at.desc())
            .limit(limit)
        )
        try:
            async with self._session_maker() as session:
                result = await session.execute(stmt)
                return [self._to_item(item) for item in result.scalars().all()]
        except SQLAlchemyError:
            logger.exception("运行摘要查询失败: task_id={}", task_id)
            return []

    async def list_latest_by_tasks(self, task_ids: list[str]) -> dict[str, SyncRunItem]:
        if not task_ids:
            return {}
        stmt = (
            select(SyncRun)
            .where(SyncRun.task_id.in_(task_ids))
            .order_by(SyncRun.task_id.asc(), SyncRun.started_at.desc(), SyncRun.updated_at.desc())
        )
        try:
            async with self._session_maker() as session:
                result = await session.execute(stmt)
                latest: dict[str, SyncRunItem] = {}
                for record in result.scalars().all():
                    if record.task_id not in latest:
                        latest[record.task_id] = self._to_item(record)
                return latest
        except SQLAlchemyError:
            logger.exception("运行摘要批量查询失败: task_ids={}", task_ids)
            return {}

    @staticmethod
    def _to_item(record: SyncRun | None) -> SyncRunItem | None:
        if record is None:
            return None
        return SyncRunItem(
            run_id=record.run_id,
            task_id=record.task_id,
            state=record.state,
            trigger_source=record.trigger_source,
            started_at=record.started_at,
            finished_at=record.finished_at,
            last_event_at=record.last_event_at,
            total_files=record.total_files,
            completed_files=record.completed_files,
            failed_files=record.failed_files,
            skipped_files=record.skipped_files,
            uploaded_files=record.uploaded_files,
            downloaded_files=record.downloaded_files,
            deleted_files=record.deleted_files,
            conflict_files=record.conflict_files,
            delete_pending_files=record.delete_pending_files,
            delete_failed_files=record.delete_failed_files,
            last_error=record.last_error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


__all__ = ["SyncRunItem", "SyncRunService"]
