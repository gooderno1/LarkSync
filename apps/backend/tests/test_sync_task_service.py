import pytest

from src.core.config import ConfigManager
from src.db.models import SyncTask
from src.db.session import get_session_maker, init_db
from src.services.sync_task_service import SyncTaskService, SyncTaskValidationError


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
    assert item.update_mode == "auto"
    assert item.md_sync_mode == "enhanced"
    assert item.is_test is False

    items = await service.list_tasks()
    assert len(items) == 1
    assert items[0].cloud_folder_token == "fld123"


@pytest.mark.asyncio
async def test_create_task_rejects_duplicate_local_path(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    await service.create_task(
        name="任务A",
        local_path="C:/docs",
        cloud_folder_token="fld-a",
        base_path=None,
        sync_mode="bidirectional",
        enabled=True,
    )
    with pytest.raises(SyncTaskValidationError, match="本地目录已绑定其它云端目录"):
        await service.create_task(
            name="任务B",
            local_path="C:/docs",
            cloud_folder_token="fld-b",
            base_path=None,
            sync_mode="bidirectional",
            enabled=True,
        )


@pytest.mark.asyncio
async def test_create_task_rejects_duplicate_cloud_folder(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    await service.create_task(
        name="任务A",
        local_path="C:/docs/a",
        cloud_folder_token="fld-a",
        base_path=None,
        sync_mode="bidirectional",
        enabled=True,
    )
    with pytest.raises(SyncTaskValidationError, match="云端目录已绑定其它本地目录"):
        await service.create_task(
            name="任务B",
            local_path="C:/docs/b",
            cloud_folder_token="fld-a",
            base_path=None,
            sync_mode="bidirectional",
            enabled=True,
        )


@pytest.mark.asyncio
async def test_create_task_rejects_nested_local_paths(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    await service.create_task(
        name="父任务",
        local_path=(tmp_path / "workspace").as_posix(),
        cloud_folder_token="fld-parent",
        cloud_folder_name="我的空间/父目录",
        base_path=None,
        sync_mode="bidirectional",
        enabled=True,
    )
    with pytest.raises(SyncTaskValidationError, match="本地目录与现有任务存在包含关系"):
        await service.create_task(
            name="子任务",
            local_path=(tmp_path / "workspace" / "sub").as_posix(),
            cloud_folder_token="fld-child",
            cloud_folder_name="我的空间/父目录/子目录",
            base_path=None,
            sync_mode="bidirectional",
            enabled=True,
        )


@pytest.mark.asyncio
async def test_update_task_rejects_mapping_conflict(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    item_a = await service.create_task(
        name="任务A",
        local_path="C:/docs/a",
        cloud_folder_token="fld-a",
        base_path=None,
        sync_mode="bidirectional",
        enabled=True,
    )
    await service.create_task(
        name="任务B",
        local_path="C:/docs/b",
        cloud_folder_token="fld-b",
        base_path=None,
        sync_mode="bidirectional",
        enabled=True,
    )

    with pytest.raises(SyncTaskValidationError, match="云端目录已绑定其它本地目录"):
        await service.update_task(
            item_a.id,
            cloud_folder_token="fld-b",
        )


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
        update_mode="partial",
        md_sync_mode="doc_only",
        enabled=False,
    )
    assert updated is not None
    assert updated.name == "任务B"
    assert updated.sync_mode == "upload_only"
    assert updated.update_mode == "partial"
    assert updated.md_sync_mode == "doc_only"
    assert updated.is_test is False
    assert updated.enabled is False


@pytest.mark.asyncio
async def test_create_task_inherits_delete_policy_from_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"delete_policy":"strict","delete_grace_minutes":99}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

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

    assert item.delete_policy == "strict"
    assert item.delete_grace_minutes == 0


@pytest.mark.asyncio
async def test_update_task_supports_delete_policy_override(tmp_path) -> None:
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

    updated = await service.update_task(
        item.id,
        delete_policy="safe",
        delete_grace_minutes=15,
    )
    assert updated is not None
    assert updated.delete_policy == "safe"
    assert updated.delete_grace_minutes == 15

    updated_strict = await service.update_task(
        item.id,
        delete_policy="strict",
        delete_grace_minutes=30,
    )
    assert updated_strict is not None
    assert updated_strict.delete_policy == "strict"
    assert updated_strict.delete_grace_minutes == 0


@pytest.mark.asyncio
async def test_list_task_resolves_legacy_null_delete_settings_from_config(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"delete_policy":"strict","delete_grace_minutes":99}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    service = SyncTaskService(session_maker=session_maker)

    item = await service.create_task(
        name="任务A",
        local_path="C:/docs",
        cloud_folder_token="fld123",
        base_path="C:/docs",
        sync_mode="bidirectional",
        enabled=True,
    )

    async with session_maker() as session:
        record = await session.get(SyncTask, item.id)
        assert record is not None
        record.delete_policy = None
        record.delete_grace_minutes = None
        await session.commit()

    listed = await service.list_tasks()
    assert len(listed) == 1
    assert listed[0].delete_policy == "strict"
    assert listed[0].delete_grace_minutes == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upload_md_to_cloud", "expected_mode"),
    [
        (False, "download_only"),
        (True, "enhanced"),
    ],
)
async def test_list_task_resolves_legacy_null_md_sync_mode_from_config(
    tmp_path,
    monkeypatch,
    upload_md_to_cloud: bool,
    expected_mode: str,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        f'{{"upload_md_to_cloud": {str(upload_md_to_cloud).lower()}}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    service = SyncTaskService(session_maker=session_maker)

    item = await service.create_task(
        name="任务A",
        local_path="C:/docs",
        cloud_folder_token="fld123",
        base_path="C:/docs",
        sync_mode="bidirectional",
        enabled=True,
    )

    async with session_maker() as session:
        record = await session.get(SyncTask, item.id)
        assert record is not None
        record.md_sync_mode = ""
        await session.commit()

    listed = await service.list_tasks()
    assert len(listed) == 1
    assert listed[0].md_sync_mode == expected_mode


@pytest.mark.asyncio
async def test_create_task_supports_is_test_flag(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncTaskService(session_maker=get_session_maker(db_url))

    item = await service.create_task(
        name="测试任务",
        local_path="C:/docs/test",
        cloud_folder_token="fld-test",
        base_path=None,
        sync_mode="download_only",
        is_test=True,
        enabled=True,
    )

    assert item.is_test is True

    listed = await service.list_tasks()
    assert len(listed) == 1
    assert listed[0].is_test is True


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


@pytest.mark.asyncio
async def test_tasks_are_isolated_by_owner_device(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service_a = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id="ou-a",
    )
    service_b = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-b",
        owner_open_id="ou-a",
    )

    created = await service_a.create_task(
        name="设备A任务",
        local_path="C:/docs/a",
        cloud_folder_token="fld-a",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
    )
    assert created.owner_device_id == "dev-a"
    assert created.owner_open_id == "ou-a"

    items_a = await service_a.list_tasks()
    items_b = await service_b.list_tasks()

    assert len(items_a) == 1
    assert items_a[0].id == created.id
    assert items_b == []


@pytest.mark.asyncio
async def test_legacy_task_without_open_id_hidden_after_account_binding(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    legacy_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id=None,
    )
    account_a_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id="ou-a",
    )
    account_b_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id="ou-b",
    )

    created = await legacy_service.create_task(
        name="历史任务",
        local_path="C:/docs/legacy",
        cloud_folder_token="fld-legacy",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
    )
    assert created.owner_open_id is None

    items_a = await account_a_service.list_tasks()
    items_b = await account_b_service.list_tasks()

    assert items_a == []
    assert items_b == []


@pytest.mark.asyncio
async def test_legacy_task_with_local_path_is_migrated_to_current_account(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    local_dir = tmp_path / "docs"
    local_dir.mkdir(parents=True, exist_ok=True)

    legacy_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id=None,
    )
    account_a_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id="ou-a",
    )
    account_b_service = SyncTaskService(
        session_maker=get_session_maker(db_url),
        owner_device_id="dev-a",
        owner_open_id="ou-b",
    )

    created = await legacy_service.create_task(
        name="本机历史任务",
        local_path=local_dir.as_posix(),
        cloud_folder_token="fld-local",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
    )
    assert created.owner_open_id is None

    original = SyncTaskService._is_local_migratable_path
    SyncTaskService._is_local_migratable_path = staticmethod(lambda _path: True)
    try:
        items_a = await account_a_service.list_tasks()
        assert len(items_a) == 1
        assert items_a[0].owner_open_id == "ou-a"

        items_b = await account_b_service.list_tasks()
        assert items_b == []
    finally:
        SyncTaskService._is_local_migratable_path = original
