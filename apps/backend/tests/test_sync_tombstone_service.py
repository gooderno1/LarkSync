import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_tombstone_service import SyncTombstoneService


@pytest.mark.asyncio
async def test_tombstone_create_refresh_keeps_earliest_expire(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTombstoneService(session_maker=get_session_maker(db_url))

    first = await service.create_or_refresh(
        task_id="task-1",
        local_path="/tmp/a.md",
        cloud_token="doc-1",
        cloud_type="docx",
        source="local",
        reason="first",
        expire_at=100.0,
    )
    second = await service.create_or_refresh(
        task_id="task-1",
        local_path="/tmp/a.md",
        cloud_token="doc-1",
        cloud_type="docx",
        source="local",
        reason="second",
        expire_at=200.0,
    )

    assert first.id == second.id
    assert second.expire_at == 100.0


@pytest.mark.asyncio
async def test_tombstone_list_and_mark_status(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTombstoneService(session_maker=get_session_maker(db_url))

    pending = await service.create_or_refresh(
        task_id="task-2",
        local_path="/tmp/b.md",
        cloud_token="doc-2",
        cloud_type="docx",
        source="cloud",
        reason="missing",
        expire_at=50.0,
    )
    items = await service.list_pending("task-2", before=100.0)
    assert len(items) == 1
    assert items[0].id == pending.id

    ok = await service.mark_status(pending.id, status="executed")
    assert ok is True

    items_after = await service.list_pending("task-2", before=100.0)
    assert items_after == []


@pytest.mark.asyncio
async def test_tombstone_failed_is_retryable_with_backoff(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTombstoneService(session_maker=get_session_maker(db_url))

    pending = await service.create_or_refresh(
        task_id="task-3",
        local_path="/tmp/c.md",
        cloud_token="doc-3",
        cloud_type="docx",
        source="local",
        reason="missing",
        expire_at=10.0,
    )
    ok = await service.mark_status(
        pending.id,
        status="failed",
        reason="retry later",
        expire_at=200.0,
    )
    assert ok is True

    not_due = await service.list_pending("task-3", before=100.0)
    assert not_due == []

    due = await service.list_pending("task-3", before=300.0)
    assert len(due) == 1
    assert due[0].id == pending.id
    assert due[0].status == "failed"

    pending_only = await service.list_pending("task-3", before=300.0, include_failed=False)
    assert pending_only == []
