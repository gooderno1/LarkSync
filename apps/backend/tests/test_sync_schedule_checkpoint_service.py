import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_run_service import SyncRunService
from src.services.sync_schedule_checkpoint_service import SyncScheduleCheckpointService


async def _finish_run(
    service: SyncRunService,
    *,
    run_id: str,
    trigger_source: str,
    finished_at: float,
) -> None:
    await service.finish_run(
        run_id=run_id,
        task_id="task-1",
        trigger_source=trigger_source,
        state="success",
        started_at=finished_at - 1,
        finished_at=finished_at,
        last_event_at=finished_at,
        total_files=0,
        completed_files=0,
        failed_files=0,
        skipped_files=0,
        uploaded_files=0,
        downloaded_files=0,
        deleted_files=0,
        conflict_files=0,
        delete_pending_files=0,
        delete_failed_files=0,
        last_error=None,
    )


@pytest.mark.asyncio
async def test_checkpoint_uses_directional_run_history_then_persisted_value(
    tmp_path,
) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'schedule.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    run_service = SyncRunService(session_maker=session_maker)
    checkpoint_service = SyncScheduleCheckpointService(session_maker=session_maker)
    await _finish_run(
        run_service,
        run_id="upload-run",
        trigger_source="scheduled_upload",
        finished_at=100.0,
    )
    await _finish_run(
        run_service,
        run_id="download-run",
        trigger_source="scheduled_download",
        finished_at=200.0,
    )

    assert await checkpoint_service.get_last_attempt("task-1", "upload") == 100.0
    assert await checkpoint_service.get_last_attempt("task-1", "download") == 200.0

    await checkpoint_service.mark_attempt("task-1", "upload", 300.0)

    assert await checkpoint_service.get_last_attempt("task-1", "upload") == 300.0
    assert await checkpoint_service.get_last_attempt("task-1", "download") == 200.0
