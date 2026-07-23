import asyncio
import time
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
        self.download_calls: list[str] = []
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
        self.download_calls.append(task.id)


class FakeCheckpointService:
    def __init__(self, values: dict[tuple[str, str], float] | None = None) -> None:
        self.values = values or {}
        self.marked: list[tuple[str, str, float]] = []

    async def get_last_attempt(self, task_id: str, direction: str) -> float | None:
        return self.values.get((task_id, direction))

    async def mark_attempt(
        self,
        task_id: str,
        direction: str,
        attempted_at: float | None = None,
    ) -> None:
        value = time.time() if attempted_at is None else attempted_at
        self.values[(task_id, direction)] = value
        self.marked.append((task_id, direction, value))


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
        checkpoint_service=FakeCheckpointService(),
        startup_grace_seconds=0,
        worker_stagger_seconds=0,
    )

    await scheduler.start()
    try:
        await asyncio.wait_for(runner.fast_event.wait(), timeout=0.2)
    finally:
        await scheduler.stop()

    assert "task-slow" in runner.upload_calls
    assert "task-fast" in runner.upload_calls


@pytest.mark.asyncio
async def test_scheduler_waits_for_startup_grace_before_running_tasks() -> None:
    runner = FakeRunner()
    task = SyncTaskItem(
        id="task-fast",
        name="启动保护测试",
        local_path="F:/fast",
        cloud_folder_token="fast-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=1.0,
        updated_at=1.0,
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
        task_service=FakeTaskService([task]),
        config_manager=config_manager,
        checkpoint_service=FakeCheckpointService(),
        startup_grace_seconds=0.05,
    )

    await scheduler.start()
    try:
        await asyncio.sleep(0.01)
        assert runner.upload_calls == []
        await asyncio.wait_for(runner.fast_event.wait(), timeout=0.2)
    finally:
        await scheduler.stop()

    assert runner.upload_calls == ["task-fast"]


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


@pytest.mark.asyncio
async def test_scheduler_restart_respects_remaining_interval() -> None:
    runner = FakeRunner()
    task = SyncTaskItem(
        id="task-existing",
        name="已运行任务",
        local_path="F:/existing",
        cloud_folder_token="existing-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=1.0,
        updated_at=1.0,
        last_run_at=time.time(),
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
        task_service=FakeTaskService([task]),
        config_manager=config_manager,
        checkpoint_service=FakeCheckpointService(),
        startup_grace_seconds=0,
        worker_stagger_seconds=0,
    )

    await scheduler.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await scheduler.stop()

    assert runner.upload_calls == []


@pytest.mark.asyncio
async def test_scheduler_checkpoints_upload_and_download_independently() -> None:
    runner = FakeRunner()
    task = SyncTaskItem(
        id="task-both",
        name="双向任务",
        local_path="F:/both",
        cloud_folder_token="both-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=1.0,
        updated_at=1.0,
    )
    now = time.time()
    checkpoint_service = FakeCheckpointService(
        {
            ("task-both", "upload"): now,
            ("task-both", "download"): now - 7200,
        }
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
        task_service=FakeTaskService([task]),
        config_manager=config_manager,
        checkpoint_service=checkpoint_service,
        startup_grace_seconds=0,
        worker_stagger_seconds=0,
    )

    await scheduler.start()
    try:
        for _ in range(20):
            if runner.download_calls:
                break
            await asyncio.sleep(0.01)
    finally:
        await scheduler.stop()

    assert runner.upload_calls == []
    assert runner.download_calls == ["task-both"]
    assert any(item[:2] == ("task-both", "download") for item in checkpoint_service.marked)
