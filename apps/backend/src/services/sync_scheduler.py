from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta

from loguru import logger

from src.core.config import ConfigManager, SyncIntervalUnit
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskService, SyncTaskItem


@dataclass
class ScheduleSnapshot:
    upload_interval_value: float
    upload_interval_unit: SyncIntervalUnit
    upload_daily_time: str
    download_interval_value: float
    download_interval_unit: SyncIntervalUnit
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
        self._upload_workers: dict[str, asyncio.Task[None]] = {}
        self._download_workers: dict[str, asyncio.Task[None]] = {}
        self._upload_task_meta: dict[str, SyncTaskItem] = {}
        self._download_task_meta: dict[str, SyncTaskItem] = {}
        self._task_refresh_interval_seconds = 1.0

    async def start(self) -> None:
        if self._upload_task or self._download_task:
            return
        if getattr(self._config_manager.config, "effective_disable_scheduler", False):
            logger.warning("当前运行配置已禁用同步调度器")
            return
        self._stop_event.clear()
        await self._ensure_watchers()
        self._upload_task = asyncio.create_task(self._upload_loop())
        self._download_task = asyncio.create_task(self._download_loop())
        logger.info("同步调度器已启动")

    async def stop(self) -> None:
        self._stop_event.set()
        for task in (
            self._upload_task,
            self._download_task,
            *self._upload_workers.values(),
            *self._download_workers.values(),
        ):
            if task:
                task.cancel()
        for task in (
            self._upload_task,
            self._download_task,
            *self._upload_workers.values(),
            *self._download_workers.values(),
        ):
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._upload_task = None
        self._download_task = None
        self._upload_workers.clear()
        self._download_workers.clear()
        self._upload_task_meta.clear()
        self._download_task_meta.clear()
        logger.info("同步调度器已停止")

    def _snapshot(self) -> ScheduleSnapshot:
        config = self._config_manager.config
        return ScheduleSnapshot(
            upload_interval_value=_safe_interval(config.upload_interval_value),
            upload_interval_unit=config.upload_interval_unit,
            upload_daily_time=config.upload_daily_time,
            download_interval_value=_safe_interval(config.download_interval_value),
            download_interval_unit=config.download_interval_unit,
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
            try:
                await self._reconcile_upload_workers()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("刷新上传调度任务失败")
            if await self._wait_for_stop(self._task_refresh_interval_seconds):
                break

    async def _download_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._reconcile_download_workers()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("刷新下载调度任务失败")
            if await self._wait_for_stop(self._task_refresh_interval_seconds):
                break

    async def _reconcile_upload_workers(self) -> None:
        tasks = await self._task_service.list_tasks()
        eligible = {task.id: task for task in tasks if _should_upload(task)}
        for task_id, worker in list(self._upload_workers.items()):
            if task_id in eligible and not worker.done():
                continue
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            self._upload_workers.pop(task_id, None)
        self._upload_task_meta = eligible
        for task in eligible.values():
            self._runner.ensure_watcher(task)
            if task.id in self._upload_workers:
                continue
            self._upload_workers[task.id] = asyncio.create_task(
                self._run_upload_worker(task.id)
            )

    async def _reconcile_download_workers(self) -> None:
        tasks = await self._task_service.list_tasks()
        eligible = {task.id: task for task in tasks if _should_download(task)}
        for task_id, worker in list(self._download_workers.items()):
            if task_id in eligible and not worker.done():
                continue
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            self._download_workers.pop(task_id, None)
        self._download_task_meta = eligible
        for task in eligible.values():
            if task.id in self._download_workers:
                continue
            self._download_workers[task.id] = asyncio.create_task(
                self._run_download_worker(task.id)
            )

    async def _run_upload_worker(self, task_id: str) -> None:
        schedule_key: tuple[object, ...] | None = None
        last_daily_run: datetime | None = None
        while not self._stop_event.is_set():
            task = self._upload_task_meta.get(task_id)
            if task is None or not _should_upload(task):
                return
            self._runner.ensure_watcher(task)
            snapshot = self._snapshot()
            key = (
                snapshot.upload_interval_unit,
                snapshot.upload_interval_value,
                snapshot.upload_daily_time,
            )
            if key != schedule_key:
                schedule_key = key
                last_daily_run = None
            if snapshot.upload_interval_unit in {
                SyncIntervalUnit.seconds,
                SyncIntervalUnit.hours,
            }:
                await self._runner.run_scheduled_upload(task)
                interval_seconds = _interval_to_seconds(
                    snapshot.upload_interval_value, snapshot.upload_interval_unit
                )
                if await self._wait_for_stop(interval_seconds):
                    return
                continue
            next_run = _next_daily_run(
                snapshot.upload_daily_time,
                interval_days=_safe_days(snapshot.upload_interval_value),
                last_run=last_daily_run,
            )
            wait_seconds = max(0.0, (next_run - datetime.now()).total_seconds())
            logger.info(
                "任务下一次本地上传计划: task_id={} time={} ({}s)",
                task.id,
                next_run.strftime("%Y-%m-%d %H:%M:%S"),
                int(wait_seconds),
            )
            if await self._wait_for_stop(wait_seconds):
                return
            task = self._upload_task_meta.get(task_id)
            if task is None or not _should_upload(task):
                return
            await self._runner.run_scheduled_upload(task)
            last_daily_run = next_run

    async def _run_download_worker(self, task_id: str) -> None:
        schedule_key: tuple[object, ...] | None = None
        last_daily_run: datetime | None = None
        while not self._stop_event.is_set():
            task = self._download_task_meta.get(task_id)
            if task is None or not _should_download(task):
                return
            snapshot = self._snapshot()
            key = (
                snapshot.download_interval_unit,
                snapshot.download_interval_value,
                snapshot.download_daily_time,
            )
            if key != schedule_key:
                schedule_key = key
                last_daily_run = None
            if snapshot.download_interval_unit in {
                SyncIntervalUnit.seconds,
                SyncIntervalUnit.hours,
            }:
                await self._runner.run_scheduled_download(task)
                interval_seconds = _interval_to_seconds(
                    snapshot.download_interval_value, snapshot.download_interval_unit
                )
                if await self._wait_for_stop(interval_seconds):
                    return
                continue
            next_run = _next_daily_run(
                snapshot.download_daily_time,
                interval_days=_safe_days(snapshot.download_interval_value),
                last_run=last_daily_run,
            )
            wait_seconds = max(0.0, (next_run - datetime.now()).total_seconds())
            logger.info(
                "任务下一次云端下载计划: task_id={} time={} ({}s)",
                task.id,
                next_run.strftime("%Y-%m-%d %H:%M:%S"),
                int(wait_seconds),
            )
            if await self._wait_for_stop(wait_seconds):
                return
            task = self._download_task_meta.get(task_id)
            if task is None or not _should_download(task):
                return
            await self._runner.run_scheduled_download(task)
            last_daily_run = next_run

    async def _wait_for_stop(self, timeout: float) -> bool:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=max(0.0, timeout))
            return True
        except asyncio.TimeoutError:
            return False


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


def _safe_days(value: float | int | None) -> int:
    try:
        days = int(float(value))
    except (TypeError, ValueError):
        return 1
    if days <= 0:
        return 1
    return days


def _interval_to_seconds(value: float, unit: SyncIntervalUnit) -> float:
    if unit == SyncIntervalUnit.hours:
        return max(1.0, value * 3600)
    return max(1.0, value)


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


def _next_daily_run(
    value: str | None,
    interval_days: int = 1,
    last_run: datetime | None = None,
    now: datetime | None = None
) -> datetime:
    now = now or datetime.now()
    target_time = _parse_daily_time(value)
    if last_run:
        candidate = last_run.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0,
        ) + timedelta(days=interval_days)
        while candidate <= now:
            candidate = candidate + timedelta(days=interval_days)
        return candidate
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
