from __future__ import annotations

import asyncio

from loguru import logger

from src.services.update_service import UpdateService


class UpdateScheduler:
    def __init__(self, update_service: UpdateService | None = None) -> None:
        self._update_service = update_service or UpdateService()
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

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
                await self._update_service.check_for_updates(force=False)
            except Exception as exc:
                logger.debug("更新检查任务异常: {}", exc)
            await asyncio.sleep(60)

    @property
    def service(self) -> UpdateService:
        return self._update_service

