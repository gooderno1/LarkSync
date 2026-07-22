import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_task_check_state_service import SyncTaskCheckStateService


@pytest.mark.asyncio
async def test_repeated_no_change_checks_update_one_task_state_row(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'check-state.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskCheckStateService(get_session_maker(db_url))

    for index in range(100):
        await service.mark_started(
            task_id="task-1",
            trigger_source="scheduled_download",
            started_at=float(index * 2),
        )
        await service.mark_finished(
            task_id="task-1",
            trigger_source="scheduled_download",
            started_at=float(index * 2),
            finished_at=float(index * 2 + 1),
            change_count=0,
        )

    states = await service.get_many(["task-1"])

    assert list(states) == ["task-1"]
    assert states["task-1"].state == "no_change"
    assert states["task-1"].consecutive_no_change == 100
    assert states["task-1"].change_count == 0


@pytest.mark.asyncio
async def test_change_and_failure_reset_no_change_counter(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'check-state.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskCheckStateService(get_session_maker(db_url))

    await service.mark_finished(
        task_id="task-1",
        trigger_source="scheduled_download",
        started_at=1.0,
        finished_at=2.0,
        change_count=0,
    )
    changed = await service.mark_finished(
        task_id="task-1",
        trigger_source="scheduled_download",
        started_at=3.0,
        finished_at=4.0,
        change_count=2,
    )
    failed = await service.mark_finished(
        task_id="task-1",
        trigger_source="scheduled_download",
        started_at=5.0,
        finished_at=6.0,
        change_count=0,
        last_error="network unavailable",
    )

    assert changed is not None
    assert changed.state == "changes_found"
    assert changed.last_change_at == 4.0
    assert failed is not None
    assert failed.state == "failed"
    assert failed.consecutive_no_change == 0
