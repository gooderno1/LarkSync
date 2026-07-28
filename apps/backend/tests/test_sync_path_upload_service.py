from __future__ import annotations

from pathlib import Path

import pytest

from src.services.sync_path_upload_service import SyncPathUploadService
from src.services.sync_runner_state import SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


class _NoLinkService:
    async def get_by_local_path(self, _path: str):
        return None


class _FailIfCalledUploader:
    async def upload_file(self, **_kwargs):
        raise AssertionError("零字节文件不应进入飞书上传器")


def _task(local_path: Path) -> SyncTaskItem:
    return SyncTaskItem(
        id="task-zero-byte",
        name="代码同步",
        local_path=str(local_path),
        cloud_folder_token="folder-token",
        cloud_folder_name="代码同步",
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=1.0,
        updated_at=1.0,
    )


@pytest.mark.asyncio
async def test_upload_file_skips_zero_byte_marker_without_failing_run(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "resource" / "package_marker"
    marker.parent.mkdir()
    marker.write_bytes(b"")
    events = []
    service = SyncPathUploadService(
        uploading_paths=set(),
        link_service=_NoLinkService(),  # type: ignore[arg-type]
        should_ignore_path=lambda _task, _path: False,
        should_upload_markdown_doc=lambda _task: True,
        upload_markdown=lambda *_args, **_kwargs: None,  # type: ignore[arg-type]
        upload_file_callback=lambda *_args, **_kwargs: None,  # type: ignore[arg-type]
        resolve_cloud_parent=lambda *_args, **_kwargs: None,  # type: ignore[arg-type]
        get_local_signature=lambda path: ("empty-hash", path.stat().st_size, path.stat().st_mtime),
        build_cloud_revision=lambda *_args: None,
        list_files_all=lambda *_args, **_kwargs: None,  # type: ignore[arg-type]
        record_event=lambda _status, event, _task: events.append(event),
    )
    status = SyncTaskStatus(task_id="task-zero-byte", state="running")

    await service.upload_file(
        _task(tmp_path),
        status,
        marker,
        _FailIfCalledUploader(),  # type: ignore[arg-type]
    )

    assert status.failed_files == 0
    assert status.completed_files == 0
    assert status.skipped_files == 1
    assert len(events) == 1
    assert events[0].status == "skipped"
    assert "0 字节" in (events[0].message or "")
