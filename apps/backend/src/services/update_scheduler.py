from __future__ import annotations

import asyncio

from loguru import logger

from src.services.update_service import UpdateService, UpdateStatus


class UpdateScheduler:
    def __init__(self, update_service: UpdateService | None = None) -> None:
        self._update_service = update_service or UpdateService()
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._last_auto_download_version: str | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                status = await self._update_service.check_for_updates(force=False)
                await self._auto_download_if_needed(status)
            except Exception as exc:
                logger.debug("更新检查任务异常: {}", exc)
            await asyncio.sleep(60)

    async def _auto_download_if_needed(self, status: UpdateStatus) -> None:
        if not self._update_service.auto_update_enabled():
            return
        if not status.update_available:
            return
        if not status.latest_version or not status.asset or not status.asset.url:
            return
        if status.latest_version == self._last_auto_download_version:
            return
        try:
            downloaded = await self._update_service.download_update()
        except Exception as exc:
            logger.warning("自动下载更新包失败: version={} error={}", status.latest_version, exc)
            return
        version = downloaded.latest_version or status.latest_version
        if downloaded.download_path:
            self._last_auto_download_version = version
            logger.info("自动更新包已下载: version={} path={}", version, downloaded.download_path)

    @property
    def service(self) -> UpdateService:
        return self._update_service
