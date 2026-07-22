from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from loguru import logger

from src.core.config import ConfigManager
from src.services.sync_event_store import SyncEventStore
from src.services.sync_run_event_service import (
    SyncRunEventBackfillResult,
    SyncRunEventService,
)


@dataclass(frozen=True)
class SyncLogMaintenanceTick:
    backfill: SyncRunEventBackfillResult
    pruned_db_events: int
    pruned_jsonl_events: int


class SyncLogMaintenanceService:
    def __init__(
        self,
        *,
        run_event_service: SyncRunEventService,
        event_store: SyncEventStore,
        config_manager: ConfigManager | None = None,
        startup_grace_seconds: float = 20.0,
    ) -> None:
        self._run_event_service = run_event_service
        self._event_store = event_store
        self._config_manager = config_manager or ConfigManager.get()
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._backfill_batch_size = 200
        self._catchup_interval_seconds = 5.0
        self._idle_interval_seconds = 30.0
        self._prune_interval_seconds = 900.0
        self._last_prune_started_at: float | None = None
        self._startup_grace_seconds = max(0.0, startup_grace_seconds)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        await self.prepare_startup()
        self._task = asyncio.create_task(self._run())
        logger.info("日志中心后台维护服务已启动")

    async def prepare_startup(self) -> bool:
        try:
            state = await self._run_event_service.get_backfill_state(self._event_store)
            if state.completed:
                return False
            if not await self._run_event_service.has_events():
                return False
            await self._run_event_service.fast_forward_backfill(self._event_store)
            logger.info(
                "SQLite 已有事件，JSONL 冗余回填断点已对齐到文件尾: old_offset={} size={}",
                state.offset,
                state.log_size,
            )
            return True
        except Exception:
            logger.exception("启动阶段日志维护准备失败，已降级为后台维护")
            return False

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        self._task = None
        logger.info("日志中心后台维护服务已停止")

    async def run_once(self) -> SyncLogMaintenanceTick:
        backfill = await self._run_event_service.backfill_step_from_event_store(
            self._event_store,
            batch_size=self._backfill_batch_size,
        )
        pruned_db_events = 0
        pruned_jsonl_events = 0
        retention_days = int(self._config_manager.config.sync_log_retention_days or 0)
        now = time.time()
        should_prune = (
            retention_days > 0
            and (
                self._last_prune_started_at is None
                or now - self._last_prune_started_at >= self._prune_interval_seconds
            )
        )
        if should_prune:
            self._last_prune_started_at = now
            pruned_db_events = await self._run_event_service.prune(
                retention_days=retention_days,
                min_interval_seconds=0,
            )
            pruned_jsonl_events = await asyncio.to_thread(
                self._event_store.prune,
                retention_days=retention_days,
                min_interval_seconds=0,
            )
        elif retention_days <= 0:
            self._last_prune_started_at = None
        return SyncLogMaintenanceTick(
            backfill=backfill,
            pruned_db_events=pruned_db_events,
            pruned_jsonl_events=pruned_jsonl_events,
        )

    async def _run(self) -> None:
        if await self._wait_for_stop(self._startup_grace_seconds):
            return
        while not self._stop_event.is_set():
            tick: SyncLogMaintenanceTick | None = None
            try:
                tick = await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("日志中心后台维护任务执行失败")
            if tick and (
                tick.backfill.inserted > 0
                or tick.backfill.skipped > 0
                or tick.pruned_db_events > 0
                or tick.pruned_jsonl_events > 0
            ):
                logger.info(
                    "日志中心后台维护完成: inserted={} skipped={} completed={} db_pruned={} jsonl_pruned={}",
                    tick.backfill.inserted,
                    tick.backfill.skipped,
                    tick.backfill.completed,
                    tick.pruned_db_events,
                    tick.pruned_jsonl_events,
                )
            delay = self._catchup_interval_seconds
            if tick and tick.backfill.completed:
                delay = self._idle_interval_seconds
            if await self._wait_for_stop(delay):
                return

    async def _wait_for_stop(self, timeout: float) -> bool:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=max(0.0, timeout))
            return True
        except asyncio.TimeoutError:
            return False


__all__ = ["SyncLogMaintenanceService", "SyncLogMaintenanceTick"]
