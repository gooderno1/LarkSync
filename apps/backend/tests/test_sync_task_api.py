import pytest

import src.api.sync_tasks as sync_tasks_api
from src.services.sync_event_store import SyncEventRecord
from src.api.sync_tasks import SyncTaskUpdateRequest, _task_update_requires_restart
from src.services.sync_run_event_service import SyncRunEventBackfillState
from src.services.sync_run_service import SyncRunItem
from src.services.sync_runner import SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


def test_task_update_requires_restart_for_ignored_subpaths() -> None:
    payload = SyncTaskUpdateRequest(ignored_subpaths=["POC/GENESIS"])
    assert _task_update_requires_restart(payload) is True


def test_task_update_does_not_require_restart_for_name_only() -> None:
    payload = SyncTaskUpdateRequest(name="新名称")
    assert _task_update_requires_restart(payload) is False


def _build_task() -> SyncTaskItem:
    return SyncTaskItem(
        id="task-1",
        name="任务A",
        local_path="D:/docs",
        cloud_folder_token="fld-1",
        cloud_folder_name="云端目录",
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=1.0,
        updated_at=2.0,
        last_run_at=20.0,
    )


def _build_run(run_id: str = "run-1") -> SyncRunItem:
    return SyncRunItem(
        run_id=run_id,
        task_id="task-1",
        state="success",
        trigger_source="manual",
        started_at=10.0,
        finished_at=20.0,
        last_event_at=20.0,
        total_files=5,
        completed_files=4,
        failed_files=1,
        skipped_files=0,
        uploaded_files=2,
        downloaded_files=2,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error="最近失败",
        created_at=10.0,
        updated_at=20.0,
    )


@pytest.mark.asyncio
async def test_get_task_diagnostics_uses_run_summary_without_scanning_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _build_task()
    run = _build_run()

    class FakeService:
        async def get_task(self, task_id: str):
            assert task_id == task.id
            return task

    class FakeRunner:
        def get_status(self, task_id: str):
            assert task_id == task.id
            return SyncTaskStatus(task_id=task.id)

    class FakeRunService:
        async def list_by_task(self, task_id: str, *, limit: int = 50):
            assert task_id == task.id
            return [run]

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("不应读取 sync-events.jsonl")

    monkeypatch.setattr(sync_tasks_api, "service", FakeService())
    monkeypatch.setattr(sync_tasks_api, "runner", FakeRunner())
    monkeypatch.setattr(sync_tasks_api, "run_service", FakeRunService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.get_task_diagnostics(
        task.id,
        limit=200,
        run_id="",
        include_events=False,
        include_problems=False,
    )

    assert response.selected_run is not None
    assert response.selected_run.run_id == run.run_id
    assert response.recent_events == []
    assert response.problems == []
    assert response.overview.counts.total == run.total_files


@pytest.mark.asyncio
async def test_get_task_diagnostics_overview_does_not_scan_events_when_run_summary_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _build_task()

    class FakeService:
        async def get_task(self, task_id: str):
            assert task_id == task.id
            return task

    class FakeRunner:
        def get_status(self, task_id: str):
            assert task_id == task.id
            return SyncTaskStatus(task_id=task.id)

    class FakeRunService:
        async def list_by_task(self, task_id: str, *, limit: int = 50):
            assert task_id == task.id
            return []

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("概览模式不应读取 sync-events.jsonl")

    monkeypatch.setattr(sync_tasks_api, "service", FakeService())
    monkeypatch.setattr(sync_tasks_api, "runner", FakeRunner())
    monkeypatch.setattr(sync_tasks_api, "run_service", FakeRunService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.get_task_diagnostics(
        task.id,
        limit=200,
        run_id="",
        include_events=False,
        include_problems=False,
    )

    assert response.selected_run is None
    assert response.recent_runs == []
    assert response.recent_events == []
    assert response.problems == []
    assert response.overview.task.id == task.id


@pytest.mark.asyncio
async def test_list_task_overview_uses_latest_run_without_scanning_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _build_task()
    run = _build_run()

    class FakeService:
        async def list_tasks(self):
            return [task]

    class FakeRunner:
        def list_statuses(self):
            return {}

    class FakeRunService:
        async def list_latest_by_tasks(self, task_ids: list[str]):
            assert task_ids == [task.id]
            return {task.id: run}

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("overview 不应读取 sync-events.jsonl")

    monkeypatch.setattr(sync_tasks_api, "service", FakeService())
    monkeypatch.setattr(sync_tasks_api, "runner", FakeRunner())
    monkeypatch.setattr(sync_tasks_api, "run_service", FakeRunService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.list_task_overview()

    assert len(response) == 1
    assert response[0].task.id == task.id
    assert response[0].counts.uploaded == run.uploaded_files
    assert response[0].counts.failed == run.failed_files


@pytest.mark.asyncio
async def test_list_task_overview_includes_delete_counts_from_latest_run_without_scanning_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _build_task()
    run = SyncRunItem(
        run_id="run-delete",
        task_id="task-1",
        state="success",
        trigger_source="manual",
        started_at=10.0,
        finished_at=20.0,
        last_event_at=20.0,
        total_files=6,
        completed_files=4,
        failed_files=1,
        skipped_files=1,
        uploaded_files=1,
        downloaded_files=1,
        deleted_files=2,
        conflict_files=0,
        delete_pending_files=1,
        delete_failed_files=1,
        last_error="最近删除失败",
        created_at=10.0,
        updated_at=20.0,
    )

    class FakeService:
        async def list_tasks(self):
            return [task]

    class FakeRunner:
        def list_statuses(self):
            return {}

    class FakeRunService:
        async def list_latest_by_tasks(self, task_ids: list[str]):
            assert task_ids == [task.id]
            return {task.id: run}

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("overview 不应读取 sync-events.jsonl")

    monkeypatch.setattr(sync_tasks_api, "service", FakeService())
    monkeypatch.setattr(sync_tasks_api, "runner", FakeRunner())
    monkeypatch.setattr(sync_tasks_api, "run_service", FakeRunService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.list_task_overview()

    assert len(response) == 1
    assert response[0].task.id == task.id
    assert response[0].counts.deleted == 2
    assert response[0].counts.delete_pending == 1
    assert response[0].counts.delete_failed == 1


@pytest.mark.asyncio
async def test_get_task_diagnostics_prefers_persisted_run_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _build_task()
    run = _build_run()
    run = SyncRunItem(**{**run.__dict__, "last_error": None})
    persisted_records = [
        SyncEventRecord(
            timestamp=20.0,
            task_id=task.id,
            task_name=task.name or "任务A",
            status="uploaded",
            path="D:/docs/a.md",
            message="上传成功",
            run_id=run.run_id,
        ),
        SyncEventRecord(
            timestamp=21.0,
            task_id=task.id,
            task_name=task.name or "任务A",
            status="failed",
            path="D:/docs/b.md",
            message="持久化错误",
            run_id=run.run_id,
        ),
    ]

    class FakeService:
        async def get_task(self, task_id: str):
            assert task_id == task.id
            return task

    class FakeRunner:
        def get_status(self, task_id: str):
            assert task_id == task.id
            return SyncTaskStatus(task_id=task.id)

    class FakeRunService:
        async def list_by_task(self, task_id: str, *, limit: int = 50):
            assert task_id == task.id
            return [run]

    class FakeRunEventService:
        async def backfill_from_event_store(self, event_store, *, batch_size: int = 200):
            return 0

        async def read_events(self, **kwargs):
            assert kwargs["task_id"] == task.id
            assert kwargs["run_id"] == run.run_id
            return len(persisted_records), persisted_records

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("不应回退读取 sync-events.jsonl")

    monkeypatch.setattr(sync_tasks_api, "service", FakeService())
    monkeypatch.setattr(sync_tasks_api, "runner", FakeRunner())
    monkeypatch.setattr(sync_tasks_api, "run_service", FakeRunService())
    monkeypatch.setattr(sync_tasks_api, "run_event_service", FakeRunEventService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.get_task_diagnostics(
        task.id,
        limit=20,
        run_id="",
        include_events=True,
        include_problems=True,
    )

    assert response.selected_run is not None
    assert response.recent_events[0].message == "上传成功"
    assert response.problems[0].message == "持久化错误"


@pytest.mark.asyncio
async def test_read_sync_logs_prefers_persisted_run_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted_records = [
        SyncEventRecord(
            timestamp=30.0,
            task_id="task-1",
            task_name="任务A",
            status="uploaded",
            path="D:/docs/a.md",
            message="上传成功",
            run_id="run-1",
        )
    ]

    class FakeRunEventService:
        async def backfill_from_event_store(self, event_store, *, batch_size: int = 200):
            return 0

        async def read_events(self, **kwargs):
            assert kwargs["run_id"] == "run-1"
            return len(persisted_records), persisted_records

        async def get_backfill_state(self, event_store):
            return SyncRunEventBackfillState(
                status="completed",
                offset=100,
                log_size=100,
                log_mtime_ns=1,
                completed=True,
            )

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("不应回退读取 sync-events.jsonl")

        def file_size_bytes(self):
            return 0

        def file_mtime_ns(self):
            return 0

    monkeypatch.setattr(sync_tasks_api, "run_event_service", FakeRunEventService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.read_sync_logs(
        limit=20,
        offset=0,
        status="",
        statuses=[],
        search="",
        task_id="",
        task_ids=[],
        run_id="run-1",
        run_ids=[],
        order="desc",
    )

    assert response.total == 1
    assert response.items[0].run_id == "run-1"


@pytest.mark.asyncio
async def test_read_sync_logs_falls_back_to_jsonl_while_backfill_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback_records = [
        SyncEventRecord(
            timestamp=40.0,
            task_id="task-1",
            task_name="任务A",
            status="failed",
            path="D:/docs/fallback.md",
            message="来自 JSONL",
            run_id="run-1",
        )
    ]

    class FakeRunEventService:
        async def read_events(self, **kwargs):
            return 0, []

        async def get_backfill_state(self, event_store):
            return SyncRunEventBackfillState(
                status="running",
                offset=10,
                log_size=100,
                log_mtime_ns=1,
                completed=False,
            )

    class FakeEventStore:
        def read_events(self, **kwargs):
            return len(fallback_records), fallback_records

        def file_size_bytes(self):
            return 0

        def file_mtime_ns(self):
            return 0

    monkeypatch.setattr(sync_tasks_api, "run_event_service", FakeRunEventService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FakeEventStore())

    response = await sync_tasks_api.read_sync_logs(
        limit=20,
        offset=0,
        status="",
        statuses=[],
        search="",
        task_id="",
        task_ids=[],
        run_id="run-1",
        run_ids=[],
        order="desc",
    )

    assert response.total == 1
    assert response.items[0].message == "来自 JSONL"


@pytest.mark.asyncio
async def test_read_sync_logs_does_not_fallback_when_backfill_completed_and_db_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRunEventService:
        async def read_events(self, **kwargs):
            return 0, []

        async def get_backfill_state(self, event_store):
            return SyncRunEventBackfillState(
                status="completed",
                offset=100,
                log_size=100,
                log_mtime_ns=1,
                completed=True,
            )

    class FailEventStore:
        def read_events(self, **kwargs):
            raise AssertionError("回填完成后不应再回退 JSONL")

        def file_size_bytes(self):
            return 0

        def file_mtime_ns(self):
            return 0

    monkeypatch.setattr(sync_tasks_api, "run_event_service", FakeRunEventService())
    monkeypatch.setattr(sync_tasks_api, "event_store", FailEventStore())

    response = await sync_tasks_api.read_sync_logs(
        limit=20,
        offset=0,
        status="",
        statuses=[],
        search="",
        task_id="",
        task_ids=[],
        run_id="run-1",
        run_ids=[],
        order="desc",
    )

    assert response.total == 0
    assert response.items == []
