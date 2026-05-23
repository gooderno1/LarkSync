from __future__ import annotations

import asyncio
from typing import Callable

from loguru import logger

from src.services.sync_event_store import SyncEventRecord
from src.services.sync_run_event_service import SyncRunEventService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem

TaskResolver = Callable[[str], SyncTaskItem | None]


class SyncEventPipeline:
    def __init__(
        self,
        *,
        event_store,
        run_event_service: SyncRunEventService,
        task_resolver: TaskResolver | None = None,
        flush_delay_seconds: float = 0.25,
        batch_size: int = 100,
    ) -> None:
        self._event_store = event_store
        self._run_event_service = run_event_service
        self._task_resolver = task_resolver
        self._flush_delay_seconds = flush_delay_seconds
        self._batch_size = max(1, batch_size)
        self._pending_records: list[SyncEventRecord] = []
        self._flush_task: asyncio.Task[None] | None = None
        self._scheduled_flush_handle: asyncio.TimerHandle | None = None
        self._flush_lock: asyncio.Lock | None = None
        self._closed = False

    def record_event(
        self,
        status: SyncTaskStatus,
        event: SyncFileEvent,
        task: SyncTaskItem | None = None,
    ) -> None:
        status.record_event(event)
        if event.status == "uploaded":
            status.uploaded_files += 1
        elif event.status == "downloaded":
            status.downloaded_files += 1
        elif event.status == "deleted":
            status.deleted_files += 1
        elif event.status == "conflict":
            status.conflict_files += 1
        elif event.status == "delete_pending":
            status.delete_pending_files += 1
        elif event.status == "delete_failed":
            status.delete_failed_files += 1
        task_info = task or (self._task_resolver(status.task_id) if self._task_resolver else None)
        task_name = (
            task_info.name
            if task_info and task_info.name
            else (task_info.local_path if task_info else "未命名任务")
        )
        record = SyncEventRecord(
            timestamp=event.timestamp,
            task_id=status.task_id,
            task_name=task_name,
            status=event.status,
            path=event.path,
            message=event.message,
            run_id=status.current_run_id if status.current_run_id else None,
        )
        self._event_store.append(record)
        self._enqueue(record)

    async def flush_now(self) -> None:
        self._cancel_scheduled_flush()
        while True:
            task = self._flush_task
            if task and not task.done():
                await task
                self._cancel_scheduled_flush()
                continue
            if not self._pending_records:
                return
            await self._flush_pending_records()

    async def close(self) -> None:
        self._closed = True
        self._cancel_scheduled_flush()
        await self.flush_now()

    def _enqueue(self, record: SyncEventRecord) -> None:
        self._pending_records.append(record)
        if self._closed:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if len(self._pending_records) >= self._batch_size:
            self._cancel_scheduled_flush()
            self._start_flush_task(loop)
            return
        if self._flush_task is None or self._flush_task.done():
            self._schedule_flush(loop, delay=self._flush_delay_seconds)

    def _schedule_flush(self, loop: asyncio.AbstractEventLoop, *, delay: float) -> None:
        if self._closed:
            return
        handle = self._scheduled_flush_handle
        if handle and not handle.cancelled():
            return
        if delay <= 0:
            self._start_flush_task(loop)
            return
        self._scheduled_flush_handle = loop.call_later(
            delay,
            self._start_scheduled_flush,
            loop,
        )

    def _start_scheduled_flush(self, loop: asyncio.AbstractEventLoop) -> None:
        self._scheduled_flush_handle = None
        if self._closed or not self._pending_records:
            return
        self._start_flush_task(loop)

    def _start_flush_task(self, loop: asyncio.AbstractEventLoop) -> None:
        task = self._flush_task
        if task is not None and not task.done():
            return
        self._flush_task = loop.create_task(self._flush_pending_records())

    def _cancel_scheduled_flush(self) -> None:
        handle = self._scheduled_flush_handle
        if handle and not handle.cancelled():
            handle.cancel()
        self._scheduled_flush_handle = None

    async def _flush_pending_records(self) -> None:
        lock = self._flush_lock
        if lock is None:
            lock = asyncio.Lock()
            self._flush_lock = lock
        try:
            async with lock:
                while self._pending_records:
                    batch = self._pending_records[: self._batch_size]
                    del self._pending_records[: self._batch_size]
                    try:
                        await self._run_event_service.append_batch(batch)
                    except Exception:
                        logger.exception("运行事件批量落库失败")
        finally:
            self._flush_task = None
            if self._closed or not self._pending_records:
                loop = None
            else:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
            if loop is not None:
                if len(self._pending_records) >= self._batch_size:
                    self._start_flush_task(loop)
                else:
                    self._schedule_flush(loop, delay=self._flush_delay_seconds)
