import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from src.core.config import SyncIntervalUnit
from src.services.sync_scheduler import SyncScheduler, _next_daily_run
from src.services.sync_task_service import SyncTaskItem


class FakeTaskService:
    def __init__(self, tasks: list[SyncTaskItem]) -> None:
        self.tasks = tasks

    async def list_tasks(self) -> list[SyncTaskItem]:
        return list(self.tasks)


class FakeRunner:
    def __init__(self) -> None:
        self.fast_event = asyncio.Event()
        self.slow_event = asyncio.Event()
        self.upload_calls: list[str] = []
        self.watchers: list[str] = []

    def ensure_watcher(self, task: SyncTaskItem) -> None:
        self.watchers.append(task.id)

    async def run_scheduled_upload(self, task: SyncTaskItem) -> None:
        self.upload_calls.append(task.id)
        if task.id == "task-slow":
            await self.slow_event.wait()
            return
        self.fast_event.set()

    async def run_scheduled_download(self, task: SyncTaskItem) -> None:
        raise AssertionError("本用例不应触发下载调度")


def test_next_daily_run_same_day() -> None:
    now = datetime(2026, 2, 6, 0, 30, 0)
    target = _next_daily_run("01:00", now=now)
    assert target == datetime(2026, 2, 6, 1, 0, 0)


def test_next_daily_run_next_day() -> None:
    now = datetime(2026, 2, 6, 1, 1, 0)
    target = _next_daily_run("01:00", now=now)
    assert target == datetime(2026, 2, 7, 1, 0, 0)


@pytest.mark.asyncio
async def test_upload_scheduler_runs_tasks_independently() -> None:
    runner = FakeRunner()
    task_service = FakeTaskService(
        [
            SyncTaskItem(
                id="task-slow",
                name="慢任务",
                local_path="F:/slow",
                cloud_folder_token="slow-token",
                cloud_folder_name=None,
                base_path=None,
                sync_mode="upload_only",
                update_mode="auto",
                enabled=True,
                created_at=2.0,
                updated_at=2.0,
            ),
            SyncTaskItem(
                id="task-fast",
                name="快任务",
                local_path="F:/fast",
                cloud_folder_token="fast-token",
                cloud_folder_name=None,
                base_path=None,
                sync_mode="upload_only",
                update_mode="auto",
                enabled=True,
                created_at=1.0,
                updated_at=1.0,
            ),
        ]
    )
    config_manager = SimpleNamespace(
        config=SimpleNamespace(
            upload_interval_value=3600.0,
            upload_interval_unit=SyncIntervalUnit.seconds,
            upload_daily_time="01:00",
            download_interval_value=3600.0,
            download_interval_unit=SyncIntervalUnit.seconds,
            download_daily_time="01:00",
        )
    )
    scheduler = SyncScheduler(
        runner=runner,
        task_service=task_service,
        config_manager=config_manager,
    )

    await scheduler.start()
    try:
        await asyncio.wait_for(runner.fast_event.wait(), timeout=0.2)
    finally:
        await scheduler.stop()

    assert "task-slow" in runner.upload_calls
    assert "task-fast" in runner.upload_calls


@pytest.mark.asyncio
async def test_scheduler_does_not_start_when_runtime_profile_disables_it() -> None:
    runner = FakeRunner()
    config_manager = SimpleNamespace(
        config=SimpleNamespace(effective_disable_scheduler=True)
    )
    scheduler = SyncScheduler(
        runner=runner,
        task_service=FakeTaskService([]),
        config_manager=config_manager,
    )

    await scheduler.start()

    assert scheduler._upload_task is None
    assert scheduler._download_task is None
