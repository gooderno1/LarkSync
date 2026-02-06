from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta

from loguru import logger

from src.core.config import ConfigManager
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskService, SyncTaskItem


@dataclass
class ScheduleSnapshot:
    upload_interval_seconds: float
    download_daily_time: str


class SyncScheduler:
    def __init__(
        self,
        runner: SyncTaskRunner,
        task_service: SyncTaskService,
        config_manager: ConfigManager | None = None,
    ) -> None:
        self._runner = runner
        self._task_service = task_service
        self._config_manager = config_manager or ConfigManager.get()
        self._stop_event = asyncio.Event()
        self._upload_task: asyncio.Task[None] | None = None
        self._download_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._upload_task or self._download_task:
            return
        self._stop_event.clear()
        await self._ensure_watchers()
        self._upload_task = asyncio.create_task(self._upload_loop())
        self._download_task = asyncio.create_task(self._download_loop())
        logger.info("同步调度器已启动")

    async def stop(self) -> None:
        self._stop_event.set()
        for task in (self._upload_task, self._download_task):
            if task:
                task.cancel()
        for task in (self._upload_task, self._download_task):
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._upload_task = None
        self._download_task = None
        logger.info("同步调度器已停止")

    def _snapshot(self) -> ScheduleSnapshot:
        config = self._config_manager.config
        return ScheduleSnapshot(
            upload_interval_seconds=_safe_interval(config.upload_interval_seconds),
            download_daily_time=config.download_daily_time,
        )

    async def _ensure_watchers(self) -> None:
        tasks = await self._task_service.list_tasks()
        for task in tasks:
            if not task.enabled:
                continue
            if task.sync_mode in {"bidirectional", "upload_only"}:
                self._runner.ensure_watcher(task)

    async def _upload_loop(self) -> None:
        while not self._stop_event.is_set():
            snapshot = self._snapshot()
            await self._trigger_uploads()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=snapshot.upload_interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    async def _trigger_uploads(self) -> None:
        tasks = await self._task_service.list_tasks()
        for task in tasks:
            if not _should_upload(task):
                continue
            self._runner.ensure_watcher(task)
            await self._runner.run_scheduled_upload(task)

    async def _download_loop(self) -> None:
        while not self._stop_event.is_set():
            snapshot = self._snapshot()
            next_run = _next_daily_run(snapshot.download_daily_time)
            wait_seconds = max(
                0.0, (next_run - datetime.now()).total_seconds()
            )
            logger.info(
                "下一次云端下载计划: {} ({}s)",
                next_run.strftime("%Y-%m-%d %H:%M:%S"),
                int(wait_seconds),
            )
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass
            if self._stop_event.is_set():
                break
            await self._trigger_downloads()

    async def _trigger_downloads(self) -> None:
        tasks = await self._task_service.list_tasks()
        for task in tasks:
            if not _should_download(task):
                continue
            await self._runner.run_scheduled_download(task)


def _should_upload(task: SyncTaskItem) -> bool:
    return task.enabled and task.sync_mode in {"bidirectional", "upload_only"}


def _should_download(task: SyncTaskItem) -> bool:
    return task.enabled and task.sync_mode in {"bidirectional", "download_only"}


def _safe_interval(value: float | int | None) -> float:
    try:
        interval = float(value)
    except (TypeError, ValueError):
        interval = 2.0
    if interval <= 0.0:
        return 2.0
    return max(0.5, interval)


def _parse_daily_time(value: str | None) -> dt_time:
    if not value:
        return dt_time(hour=1, minute=0)
    parts = value.strip().split(":")
    if len(parts) != 2:
        return dt_time(hour=1, minute=0)
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return dt_time(hour=1, minute=0)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return dt_time(hour=1, minute=0)
    return dt_time(hour=hour, minute=minute)


def _next_daily_run(value: str | None, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    target_time = _parse_daily_time(value)
    target = now.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target = target + timedelta(days=1)
    return target


__all__ = ["SyncScheduler", "ScheduleSnapshot"]
