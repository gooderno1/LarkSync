import asyncio
from types import SimpleNamespace

import pytest

from src.api.sync_task_models import SyncTaskStatusResponse
from src.services.sync_runner_state import SyncTaskStatus
from src.services.sync_runtime import SyncRuntime, current_runtime, runtime_scope, runtime_wait


def test_unknown_scan_and_each_direction_have_separate_counts():
    runtime = SyncRuntime()
    runtime.begin_phase("scanning_cloud", direction="download")
    runtime.discover(372)
    scan = runtime.snapshot()
    assert scan.total is None
    assert scan.discovered == 372
    runtime.begin_phase("downloading", direction="download", total=2)
    runtime.set_current("a.md")
    runtime.advance()
    runtime.advance()
    downloaded = runtime.snapshot()
    assert (downloaded.processed, downloaded.total) == (2, 2)
    runtime.begin_phase("uploading", direction="upload", total=3)
    uploaded = runtime.snapshot()
    assert (uploaded.processed, uploaded.total) == (0, 3)
    assert uploaded.segment_id != downloaded.segment_id
    assert uploaded.processed_total == 2
    assert uploaded.current_item is None


def test_elapsed_uses_monotonic_clock_and_freezes_after_finish(monkeypatch):
    now = [1000.0]
    monotonic = [10.0]
    monkeypatch.setattr("src.services.sync_runtime.time.time", lambda: now[0])
    monkeypatch.setattr("src.services.sync_runtime.time.monotonic", lambda: monotonic[0])
    runtime = SyncRuntime()
    now[0] = 500.0  # System clock correction must not make elapsed negative.
    monotonic[0] = 75.0
    assert runtime.snapshot().elapsed_seconds == 65
    runtime.finish()
    monotonic[0] = 1000
    assert runtime.snapshot().elapsed_seconds == 65
    runtime.advance()
    runtime.begin_phase("uploading", total=100)
    assert runtime.snapshot().phase == "finished"
    assert runtime.snapshot().processed_total == 0


def test_waits_restore_outer_reason_and_do_not_invent_progress():
    runtime = SyncRuntime()
    runtime.begin_phase("downloading", total=2)
    before = runtime.snapshot().progress_at
    with runtime_scope(runtime):
        with runtime_wait("remote_export"):
            assert runtime.snapshot().wait.reason == "remote_export"
            with runtime_wait("rate_limit", delay=8, attempt=2):
                wait = runtime.snapshot().wait
                assert wait.reason == "rate_limit"
                assert wait.resume_at == pytest.approx(wait.since + 8)
                assert wait.attempt == 2
            assert runtime.snapshot().wait.reason == "remote_export"
        assert runtime.snapshot().wait is None
    assert runtime.snapshot().processed == 0
    assert runtime.snapshot().progress_at == before
    assert current_runtime() is None


@pytest.mark.asyncio
async def test_wait_contexts_are_isolated_between_tasks_and_cancel_cleans_up():
    first, second = SyncRuntime(), SyncRuntime()
    entered = asyncio.Event()

    async def blocked():
        with runtime_scope(first), runtime_wait("retry", delay=10):
            entered.set()
            await asyncio.Event().wait()

    pending = asyncio.create_task(blocked())
    await entered.wait()
    with runtime_scope(second):
        assert current_runtime() is second
        assert second.snapshot().wait is None
        assert first.snapshot().wait.reason == "retry"
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert first.snapshot().wait is None
    assert current_runtime() is None


def test_api_snapshot_is_additive_and_polling_does_not_advance_worker():
    status = SyncTaskStatus(task_id="task-a")
    assert SyncTaskStatusResponse.from_status(status).model_dump()["runtime"] is None
    status.runtime = SyncRuntime()
    status.runtime.begin_phase("scanning_local", direction="upload")
    first = SyncTaskStatusResponse.from_status(status).model_dump()["runtime"]
    second = SyncTaskStatusResponse.from_status(status).model_dump()["runtime"]
    assert first["execution_id"] == second["execution_id"]
    assert first["activity_at"] == second["activity_at"]
    assert first["progress_at"] == second["progress_at"]
    assert first["total"] is None
    assert "speed" not in first and "eta" not in first


@pytest.mark.asyncio
async def test_token_bucket_only_reports_wait_during_actual_sleep(monkeypatch):
    from src.services.rate_limiter import AsyncTokenBucket

    clock = [10.0]
    monkeypatch.setattr("src.services.rate_limiter.time.monotonic", lambda: clock[0])
    observation = SyncRuntime()
    waits = []
    async def sleep(delay):
        waits.append(observation.snapshot().wait.reason)
        clock[0] += delay
    monkeypatch.setattr("src.services.rate_limiter.asyncio.sleep", sleep)
    limiter = AsyncTokenBucket(1, 1)
    with runtime_scope(observation):
        await limiter.acquire()
        assert waits == []
        await limiter.acquire()
    assert waits == ["local_rate_limit"]
    assert observation.snapshot().wait is None


@pytest.mark.asyncio
async def test_export_poll_observes_remote_wait_and_next_query_not_finish_eta(monkeypatch):
    from src.services.sync_download_support_service import SyncDownloadSupportService

    observation = SyncRuntime()
    seen = []
    class Export:
        async def get_export_task_result(self, *args, **kwargs):
            seen.append(observation.snapshot().wait)
            return SimpleNamespace(job_status=1 if len(seen) == 1 else 0, job_error_msg=None, file_token="file-a")
    async def sleep(delay):
        wait = observation.snapshot().wait
        assert wait.reason == "remote_export"
        assert wait.resume_at == pytest.approx(wait.since + delay)
    monkeypatch.setattr("src.services.sync_download_support_service.asyncio.sleep", sleep)
    with runtime_scope(observation):
        result = await SyncDownloadSupportService.__new__(SyncDownloadSupportService).wait_for_export_task(
            Export(), "ticket", poll_attempts=3, poll_interval=2,
        )
    assert result.file_token == "file-a"
    assert all(wait.reason == "remote_export" and wait.resume_at is None for wait in seen)
    assert observation.snapshot().wait is None


@pytest.mark.asyncio
async def test_scheduled_initial_scan_is_visible_but_empty_check_preserves_previous_run(tmp_path, monkeypatch):
    from src.services.sync_runner import SyncTaskRunner
    from src.services.sync_task_service import SyncTaskItem

    runner = SyncTaskRunner()
    task = SyncTaskItem(
        id="scan", name="scan", local_path=str(tmp_path), cloud_folder_token="root",
        cloud_folder_name=None, base_path=None, sync_mode="upload_only", update_mode="auto",
        enabled=True, created_at=0, updated_at=0,
    )
    previous = SyncRuntime()
    previous.finish()
    status = SyncTaskStatus(task_id=task.id, state="success", started_at=1, runtime=previous)
    runner._statuses[task.id] = status
    async def scan(task_arg):
        snapshot = runner.get_status(task_arg.id).runtime.snapshot()
        assert snapshot.active and snapshot.phase == "scanning_local"
        assert snapshot.execution_id != previous.execution_id
    async def no_deletes(*args):
        return False
    monkeypatch.setattr(runner, "_scan_for_unlinked_files", scan)
    monkeypatch.setattr(runner, "_has_pending_tombstones", no_deletes)
    await runner.run_scheduled_upload(task)
    assert status.runtime is previous
    assert status.state == "success"
    assert status.current_run_id is None
    assert status.last_files == []


@pytest.mark.asyncio
async def test_finalization_failure_still_closes_runtime(monkeypatch):
    from src.services.sync_runner import SyncTaskRunner

    runner = SyncTaskRunner()
    observation = SyncRuntime()
    status = SyncTaskStatus(task_id="task-a", state="failed", runtime=observation)
    async def flush():
        assert observation.snapshot().phase == "finalizing"
        raise RuntimeError("write failed")
    monkeypatch.setattr(runner, "_flush_pending_events_now", flush)
    with pytest.raises(RuntimeError, match="write failed"):
        await runner._finalize_run_status(SimpleNamespace(id="task-a"), status)
    assert not observation.snapshot().active


@pytest.mark.asyncio
async def test_preflight_does_not_replace_a_run_started_during_signature_check(tmp_path, monkeypatch):
    from src.services.sync_runner import SyncTaskRunner
    from src.services.sync_task_service import SyncTaskItem

    runner = SyncTaskRunner()
    task = SyncTaskItem(
        id="race", name="race", local_path=str(tmp_path), cloud_folder_token="root",
        cloud_folder_name=None, base_path=None, sync_mode="upload_only", update_mode="auto",
        enabled=True, created_at=0, updated_at=0,
    )
    path = tmp_path / "a.md"
    runner._initial_upload_scanned.add(task.id)
    runner._pending_uploads[task.id] = {str(path): 0}
    replacement = SyncRuntime()

    async def no_deletes(*args):
        return False

    async def check(task_arg, paths):
        status = runner.get_status(task_arg.id)
        status.runtime.finish()
        status.runtime = replacement
        status.state = "running"
        runner._running_tasks.add(task_arg.id)
        return paths

    monkeypatch.setattr(runner, "_has_pending_tombstones", no_deletes)
    monkeypatch.setattr(runner, "_filter_unchanged_ready_paths", check)
    await runner.run_scheduled_upload(task)
    assert runner.get_status(task.id).runtime is replacement
    assert replacement.active
    assert str(path) in runner._pending_uploads[task.id]
