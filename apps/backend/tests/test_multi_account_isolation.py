from __future__ import annotations

import pytest

from src.core.account_context import account_scope
from src.db.session import get_session_maker, init_db
from src.services.conflict_service import ConflictService
from src.services.sync_link_service import SyncLinkService
from src.services.sync_task_service import SyncTaskService


@pytest.mark.asyncio
async def test_services_isolate_records_for_one_long_lived_instance(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'accounts.db').as_posix()}"
    await init_db(db_url)
    maker = get_session_maker(db_url)
    tasks = SyncTaskService(
        session_maker=maker,
        owner_device_id="device-1",
        owner_open_id=None,
    )
    links = SyncLinkService(session_maker=maker)
    conflicts = ConflictService(session_maker=maker)

    with account_scope("account-a"):
        task_a = await tasks.create_task(
            name="A",
            local_path=str(tmp_path / "a"),
            cloud_folder_token="folder-a",
            base_path=None,
            sync_mode="bidirectional",
        )
        await links.upsert_link(
            local_path=str(tmp_path / "shared.md"),
            cloud_token="doc-a",
            cloud_type="docx",
            task_id=task_a.id,
        )
        conflict_a = await conflicts.add_conflict(
            local_path=str(tmp_path / "a.md"),
            cloud_token="doc-a",
            local_hash="a",
            db_hash="base",
            cloud_version=2,
            db_version=1,
        )

    with account_scope("account-b"):
        task_b = await tasks.create_task(
            name="B",
            local_path=str(tmp_path / "b"),
            cloud_folder_token="folder-b",
            base_path=None,
            sync_mode="bidirectional",
        )
        await links.upsert_link(
            local_path=str(tmp_path / "shared.md"),
            cloud_token="doc-b",
            cloud_type="docx",
            task_id=task_b.id,
        )
        conflict_b = await conflicts.add_conflict(
            local_path=str(tmp_path / "b.md"),
            cloud_token="doc-b",
            local_hash="b",
            db_hash="base",
            cloud_version=2,
            db_version=1,
        )

    with account_scope("account-a"):
        assert [item.id for item in await tasks.list_tasks()] == [task_a.id]
        assert await tasks.get_task(task_b.id) is None
        assert (await links.get_by_local_path(str(tmp_path / "shared.md"))).cloud_token == "doc-a"  # type: ignore[union-attr]
        assert {item.account_id for item in await conflicts.list_conflicts()} == {"account-a"}
        assert await conflicts.get_conflict(conflict_a.id) is not None
        assert await conflicts.get_conflict(conflict_b.id) is None

    with account_scope("account-b"):
        assert [item.id for item in await tasks.list_tasks()] == [task_b.id]
        assert await tasks.get_task(task_a.id) is None
        assert (await links.get_by_local_path(str(tmp_path / "shared.md"))).cloud_token == "doc-b"  # type: ignore[union-attr]
        assert {item.account_id for item in await conflicts.list_conflicts()} == {"account-b"}
        assert await conflicts.get_conflict(conflict_b.id) is not None
        assert await conflicts.get_conflict(conflict_a.id) is None
