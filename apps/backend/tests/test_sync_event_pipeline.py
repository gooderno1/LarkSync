from __future__ import annotations

import pytest

from src.services.sync_event_pipeline import SyncEventPipeline
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus


class _FakeEventStore:
    def __init__(self) -> None:
        self.records = []

    def append(self, record) -> None:
        self.records.append(record)


class _FakeRunEventService:
    def __init__(self) -> None:
        self.batches: list[list[object]] = []

    async def append_batch(self, batch: list[object]) -> None:
        self.batches.append(list(batch))


@pytest.mark.asyncio
async def test_record_event_updates_status_and_persists_with_task_resolver() -> None:
    event_store = _FakeEventStore()
    run_event_service = _FakeRunEventService()
    task = type("Task", (), {"id": "task-1", "name": "知识库同步", "local_path": "D:/Docs"})()
    status = SyncTaskStatus(task_id="task-1", current_run_id="run-1")
    pipeline = SyncEventPipeline(
        event_store=event_store,
        run_event_service=run_event_service,
        task_resolver=lambda task_id: task if task_id == "task-1" else None,
        flush_delay_seconds=999.0,
        batch_size=10,
    )

    pipeline.record_event(
        status,
        SyncFileEvent(path="D:/Docs/spec.md", status="uploaded", message="ok", timestamp=100.0),
    )
    await pipeline.flush_now()

    assert status.uploaded_files == 1
    assert len(status.last_files) == 1
    assert len(event_store.records) == 1
    record = event_store.records[0]
    assert record.task_name == "知识库同步"
    assert record.path == "D:/Docs/spec.md"
    assert record.run_id == "run-1"
    assert len(run_event_service.batches) == 1
    assert run_event_service.batches[0][0].task_id == "task-1"


@pytest.mark.asyncio
async def test_record_event_uses_default_task_name_when_task_missing() -> None:
    event_store = _FakeEventStore()
    run_event_service = _FakeRunEventService()
    status = SyncTaskStatus(task_id="task-2")
    pipeline = SyncEventPipeline(
        event_store=event_store,
        run_event_service=run_event_service,
        task_resolver=lambda task_id: None,
        flush_delay_seconds=999.0,
        batch_size=10,
    )

    pipeline.record_event(
        status,
        SyncFileEvent(path="D:/Docs/error.md", status="conflict", message="冲突", timestamp=200.0),
    )
    await pipeline.flush_now()

    assert status.conflict_files == 1
    assert event_store.records[0].task_name == "未命名任务"

