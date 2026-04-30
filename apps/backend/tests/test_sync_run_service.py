import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_run_service import SyncRunService


@pytest.mark.asyncio
async def test_sync_run_service_start_and_finish_run(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunService(session_maker=get_session_maker(db_url))

    started = await service.start_run(
        run_id="run-1",
        task_id="task-1",
        trigger_source="manual",
        started_at=100.0,
    )
    assert started.run_id == "run-1"
    assert started.state == "running"
    assert started.started_at == 100.0

    finished = await service.finish_run(
        run_id="run-1",
        task_id="task-1",
        trigger_source="manual",
        state="success",
        started_at=100.0,
        finished_at=120.0,
        last_event_at=121.0,
        total_files=4,
        completed_files=3,
        failed_files=1,
        skipped_files=0,
        uploaded_files=2,
        downloaded_files=1,
        deleted_files=0,
        conflict_files=1,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error="boom",
    )
    assert finished.state == "success"
    assert finished.finished_at == 120.0
    assert finished.last_event_at == 121.0
    assert finished.uploaded_files == 2
    assert finished.conflict_files == 1
    assert finished.last_error == "boom"

    listed = await service.list_by_task("task-1")
    assert [item.run_id for item in listed] == ["run-1"]
    assert listed[0].uploaded_files == 2


@pytest.mark.asyncio
async def test_sync_run_service_lists_latest_by_tasks(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunService(session_maker=get_session_maker(db_url))

    await service.finish_run(
        run_id="run-old",
        task_id="task-1",
        trigger_source="manual",
        state="failed",
        started_at=10.0,
        finished_at=11.0,
        last_event_at=11.0,
        total_files=1,
        completed_files=0,
        failed_files=1,
        skipped_files=0,
        uploaded_files=0,
        downloaded_files=0,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error="old",
    )
    await service.finish_run(
        run_id="run-new",
        task_id="task-1",
        trigger_source="scheduled_upload",
        state="success",
        started_at=20.0,
        finished_at=22.0,
        last_event_at=22.0,
        total_files=2,
        completed_files=2,
        failed_files=0,
        skipped_files=0,
        uploaded_files=2,
        downloaded_files=0,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error=None,
    )
    await service.finish_run(
        run_id="run-other",
        task_id="task-2",
        trigger_source="scheduled_download",
        state="success",
        started_at=30.0,
        finished_at=32.0,
        last_event_at=32.0,
        total_files=1,
        completed_files=1,
        failed_files=0,
        skipped_files=0,
        uploaded_files=0,
        downloaded_files=1,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error=None,
    )

    latest = await service.list_latest_by_tasks(["task-1", "task-2"])
    assert latest["task-1"].run_id == "run-new"
    assert latest["task-2"].run_id == "run-other"
