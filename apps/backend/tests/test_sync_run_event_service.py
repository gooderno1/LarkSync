import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_run_event_service import (
    SyncRunEventAppendResult,
    SyncRunEventService,
)


@pytest.mark.asyncio
async def test_sync_run_event_service_append_and_filter(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunEventService(session_maker=get_session_maker(db_url))

    await service.append_batch(
        [
            SyncEventRecord(
                timestamp=1.0,
                task_id="task-1",
                task_name="任务A",
                status="started",
                path="/tmp/a",
                message="开始",
                run_id="run-1",
            ),
            SyncEventRecord(
                timestamp=2.0,
                task_id="task-1",
                task_name="任务A",
                status="failed",
                path="/tmp/a.md",
                message="boom",
                run_id="run-1",
            ),
            SyncEventRecord(
                timestamp=3.0,
                task_id="task-2",
                task_name="任务B",
                status="uploaded",
                path="/tmp/b.md",
                message="ok",
                run_id="run-2",
            ),
        ]
    )

    total, items = await service.read_events(
        limit=10,
        offset=0,
        status="",
        statuses=["failed", "uploaded"],
        search="",
        task_id="",
        task_ids=[],
        run_id="",
        run_ids=[],
        order="desc",
    )
    assert total == 2
    assert [item.status for item in items] == ["uploaded", "failed"]

    total, items = await service.read_events(
        limit=10,
        offset=0,
        status="",
        statuses=[],
        search="boom",
        task_id="task-1",
        task_ids=[],
        run_id="run-1",
        run_ids=[],
        order="desc",
    )
    assert total == 1
    assert items[0].message == "boom"


@pytest.mark.asyncio
async def test_sync_run_event_service_backfills_jsonl_idempotently(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunEventService(session_maker=get_session_maker(db_url))
    store = SyncEventStore(tmp_path / "sync-events.jsonl")
    store.append(
        SyncEventRecord(
            timestamp=10.0,
            task_id="task-1",
            task_name="任务A",
            status="downloaded",
            path="/tmp/a.md",
            message="ok",
            run_id="run-1",
        )
    )

    inserted = await service.backfill_from_event_store(store, batch_size=2)
    assert inserted == 1

    inserted_again = await service.backfill_from_event_store(store, batch_size=2)
    assert inserted_again == 0

    total, items = await service.read_events(
        limit=10,
        offset=0,
        status="",
        statuses=[],
        search="",
        task_id="task-1",
        task_ids=[],
        run_id="run-1",
        run_ids=[],
        order="desc",
    )
    assert total == 1
    assert items[0].path == "/tmp/a.md"


@pytest.mark.asyncio
async def test_sync_run_event_service_backfill_step_tracks_checkpoint_and_new_lines(
    tmp_path,
) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunEventService(session_maker=get_session_maker(db_url))
    store = SyncEventStore(tmp_path / "sync-events.jsonl")
    store.append(
        SyncEventRecord(
            timestamp=10.0,
            task_id="task-1",
            task_name="任务A",
            status="started",
            path="/tmp/a.md",
            message="开始",
            run_id="run-1",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=11.0,
            task_id="task-1",
            task_name="任务A",
            status="failed",
            path="/tmp/b.md",
            message="失败",
            run_id="run-1",
        )
    )

    first = await service.backfill_step_from_event_store(store, batch_size=1)
    assert first.inserted == 1
    assert first.completed is False
    assert first.offset > 0

    state_after_first = await service.get_backfill_state(store)
    assert state_after_first.offset == first.offset
    assert state_after_first.completed is False

    second = await service.backfill_step_from_event_store(store, batch_size=1)
    assert second.inserted == 1
    assert second.completed is True

    store.append(
        SyncEventRecord(
            timestamp=12.0,
            task_id="task-1",
            task_name="任务A",
            status="uploaded",
            path="/tmp/c.md",
            message="补写",
            run_id="run-2",
        )
    )

    third = await service.backfill_step_from_event_store(store, batch_size=10)
    assert third.inserted == 1
    assert third.completed is True

    total, items = await service.read_events(
        limit=10,
        offset=0,
        status="",
        statuses=[],
        search="",
        task_id="task-1",
        task_ids=[],
        run_id="",
        run_ids=[],
        order="asc",
    )
    assert total == 3
    assert [item.path for item in items] == ["/tmp/a.md", "/tmp/b.md", "/tmp/c.md"]


@pytest.mark.asyncio
async def test_sync_run_event_service_backfill_step_does_not_advance_on_write_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncRunEventService(session_maker=get_session_maker(db_url))
    store = SyncEventStore(tmp_path / "sync-events.jsonl")
    store.append(
        SyncEventRecord(
            timestamp=10.0,
            task_id="task-1",
            task_name="任务A",
            status="downloaded",
            path="/tmp/a.md",
            message="ok",
            run_id="run-1",
        )
    )

    async def fail_append(records):
        return SyncRunEventAppendResult(inserted=0, attempted=len(records), succeeded=False)

    monkeypatch.setattr(service, "_append_batch_result", fail_append)

    result = await service.backfill_step_from_event_store(store, batch_size=10)
    assert result.inserted == 0
    assert result.completed is False
    assert result.offset == 0

    state = await service.get_backfill_state(store)
    assert state.offset == 0
    assert state.completed is False
