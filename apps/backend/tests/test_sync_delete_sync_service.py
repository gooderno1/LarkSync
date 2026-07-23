import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.sync_delete_sync_service import SyncDeleteSyncService
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_runner_state import SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


class _LinkService:
    def __init__(self, link: SyncLinkItem | None = None) -> None:
        self.link = link

    async def get_by_local_path(self, local_path: str):
        return self.link


class _TombstoneService:
    def __init__(self, *, created: bool = True) -> None:
        self.created = created
        self.before_values: list[float | None] = []

    async def list_pending(self, task_id: str, *, before: float | None = None):
        self.before_values.append(before)
        if before is None:
            return [SimpleNamespace(id="future")]
        return []

    async def create_or_refresh(self, **kwargs):
        return SimpleNamespace(created=self.created)


def _service(link_service, tombstone_service) -> SyncDeleteSyncService:
    return SyncDeleteSyncService(
        link_service=link_service,
        tombstone_service=tombstone_service,
        block_service=SimpleNamespace(),
        should_ignore_path=lambda task, path: False,
        local_trash_dir_name=".trash",
    )


@pytest.mark.asyncio
async def test_pending_tombstone_check_only_returns_due_items() -> None:
    tombstones = _TombstoneService()
    service = _service(_LinkService(), tombstones)

    has_pending = await service.has_pending_tombstones("task-1")

    assert has_pending is False
    assert tombstones.before_values
    assert tombstones.before_values[0] is not None
    assert abs(float(tombstones.before_values[0]) - time.time()) < 2


@pytest.mark.asyncio
async def test_refreshed_tombstone_does_not_emit_duplicate_pending_event(
    tmp_path: Path,
) -> None:
    local_path = tmp_path / "deleted.md"
    link = SyncLinkItem(
        local_path=str(local_path),
        cloud_token="doc-1",
        cloud_type="docx",
        task_id="task-1",
        updated_at=1.0,
    )
    service = _service(_LinkService(link), _TombstoneService(created=False))
    task = SyncTaskItem(
        id="task-1",
        name="删除事件去重",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)
    events: list[object] = []

    result = await service.enqueue_local_delete_tombstone(
        task=task,
        status=status,
        local_path=local_path,
        reason="检测到本地已删除",
        record_event=lambda *_args: events.append(_args[1]),
    )

    assert result is False
    assert events == []


def test_cloud_not_found_token_error_is_idempotent_success() -> None:
    error = RuntimeError("删除文件失败: not found. token=folder-1 type=folder")

    assert SyncDeleteSyncService.is_cloud_already_deleted_error(error) is True
