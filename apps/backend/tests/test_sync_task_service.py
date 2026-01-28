import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_task_service import SyncTaskService


@pytest.mark.asyncio
async def test_create_and_list_tasks(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    item = await service.create_task(
        name="任务A",
        local_path="C:/docs",
        cloud_folder_token="fld123",
        base_path="C:/docs",
        sync_mode="bidirectional",
        enabled=True,
    )
    assert item.id
    assert item.local_path == "C:/docs"

    items = await service.list_tasks()
    assert len(items) == 1
    assert items[0].cloud_folder_token == "fld123"


@pytest.mark.asyncio
async def test_update_task_fields(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    item = await service.create_task(
        name=None,
        local_path="C:/docs",
        cloud_folder_token="fld123",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
    )

    updated = await service.update_task(
        item.id,
        name="任务B",
        sync_mode="upload_only",
        enabled=False,
    )
    assert updated is not None
    assert updated.name == "任务B"
    assert updated.sync_mode == "upload_only"
    assert updated.enabled is False


@pytest.mark.asyncio
async def test_delete_task(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    item = await service.create_task(
        name="待删除",
        local_path="C:/docs",
        cloud_folder_token="fld123",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
    )

    deleted = await service.delete_task(item.id)
    assert deleted is True

    missing = await service.get_task(item.id)
    assert missing is None
