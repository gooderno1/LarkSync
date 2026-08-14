from __future__ import annotations

from pathlib import Path

import pytest

from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem
from src.services.sync_upload_orchestration_service import (
    SyncUploadOrchestrationService,
    UploadRuntimeServices,
)


class _Closable:
    async def close(self) -> None:
        return None


def _task(tmp_path: Path) -> SyncTaskItem:
    return SyncTaskItem(
        id="task-upload-race",
        name="上传竞态",
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


def _runtime() -> UploadRuntimeServices:
    return UploadRuntimeServices(
        docx_service=_Closable(),  # type: ignore[arg-type]
        file_uploader=_Closable(),  # type: ignore[arg-type]
        drive_service=_Closable(),  # type: ignore[arg-type]
        import_task_service=_Closable(),  # type: ignore[arg-type]
        owned_services=[],
    )


def _service(upload_path, events: list[SyncFileEvent]) -> SyncUploadOrchestrationService:
    async def _noop(*args, **kwargs) -> None:
        return None

    return SyncUploadOrchestrationService(
        prefill_links_from_cloud=_noop,
        enqueue_missing_local_deletes=_noop,
        iter_local_files=lambda task: [],
        upload_path=upload_path,
        process_pending_deletes=_noop,
        record_event=lambda status, event, task: events.append(event),
    )


@pytest.mark.asyncio
async def test_upload_path_disappearing_midflight_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "moved.md"
    path.write_text("# moved", encoding="utf-8")
    events: list[SyncFileEvent] = []

    async def _upload_path(*args, **kwargs) -> None:
        path.unlink()
        raise FileNotFoundError(2, "No such file or directory", str(path))

    service = _service(_upload_path, events)
    status = SyncTaskStatus(task_id="task-upload-race")

    await service.run_upload_paths(
        task=_task(tmp_path),
        status=status,
        paths=[path],
        runtime=_runtime(),
        allow_deletes=False,
    )

    assert status.failed_files == 0
    assert status.skipped_files == 1
    assert [(event.status, event.message) for event in events] == [
        ("skipped", "源文件已移动或删除，取消旧路径上传")
    ]


@pytest.mark.asyncio
async def test_empty_upload_exception_uses_exception_type_as_message(tmp_path: Path) -> None:
    path = tmp_path / "existing.md"
    path.write_text("# existing", encoding="utf-8")
    events: list[SyncFileEvent] = []

    async def _upload_path(*args, **kwargs) -> None:
        raise RuntimeError()

    service = _service(_upload_path, events)
    status = SyncTaskStatus(task_id="task-upload-race")

    await service.run_upload_paths(
        task=_task(tmp_path),
        status=status,
        paths=[path],
        runtime=_runtime(),
        allow_deletes=False,
    )

    assert status.failed_files == 1
    assert status.last_error == "RuntimeError()"
    assert events[0].message == "RuntimeError()"
