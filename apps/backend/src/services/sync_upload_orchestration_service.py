from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from loguru import logger

from src.services.docx_service import DocxService
from src.services.drive_service import DriveService
from src.services.file_uploader import FileUploader
from src.services.import_task_service import ImportTaskService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem

PrefillLinksFn = Callable[[SyncTaskItem, DriveService], Awaitable[None]]
EnqueueMissingLocalDeletesFn = Callable[..., Awaitable[None]]
IterLocalFilesFn = Callable[[SyncTaskItem], Iterable[Path]]
UploadPathFn = Callable[..., Awaitable[None]]
ProcessPendingDeletesFn = Callable[..., Awaitable[None]]
RecordEventFn = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]


@dataclass
class UploadRuntimeServices:
    docx_service: DocxService
    file_uploader: FileUploader
    drive_service: DriveService
    import_task_service: ImportTaskService
    owned_services: list[Any]


class SyncUploadOrchestrationService:
    def __init__(
        self,
        *,
        prefill_links_from_cloud: PrefillLinksFn,
        enqueue_missing_local_deletes: EnqueueMissingLocalDeletesFn,
        iter_local_files: IterLocalFilesFn,
        upload_path: UploadPathFn,
        process_pending_deletes: ProcessPendingDeletesFn,
        record_event: RecordEventFn,
    ) -> None:
        self._prefill_links_from_cloud = prefill_links_from_cloud
        self._enqueue_missing_local_deletes = enqueue_missing_local_deletes
        self._iter_local_files = iter_local_files
        self._upload_path = upload_path
        self._process_pending_deletes = process_pending_deletes
        self._record_event = record_event

    async def run_upload(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        runtime: UploadRuntimeServices,
        allow_deletes: bool = True,
    ) -> None:
        try:
            if task.sync_mode == "upload_only":
                await self._prefill_links_from_cloud(task, runtime.drive_service)
            if allow_deletes:
                await self._enqueue_missing_local_deletes(task=task, status=status)
            files = list(self._iter_local_files(task))
            logger.info("上传阶段: task_id={} files={}", task.id, len(files))
            status.total_files += len(files)
            for path in files:
                await self._upload_with_guard(
                    task=task,
                    status=status,
                    path=path,
                    runtime=runtime,
                    force=False,
                )
            if allow_deletes:
                await self._process_pending_deletes(
                    task=task,
                    status=status,
                    drive_service=runtime.drive_service,
                )
        finally:
            await self._close_owned_services(runtime)

    async def run_upload_paths(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        paths: Iterable[Path],
        runtime: UploadRuntimeServices,
        allow_deletes: bool = True,
        force_paths: set[str] | None = None,
    ) -> None:
        try:
            if task.sync_mode == "upload_only":
                await self._prefill_links_from_cloud(task, runtime.drive_service)
            if allow_deletes:
                await self._enqueue_missing_local_deletes(task=task, status=status)
            path_list = list(paths)
            status.total_files += len(path_list)
            for path in path_list:
                await self._upload_with_guard(
                    task=task,
                    status=status,
                    path=path,
                    runtime=runtime,
                    force=bool(force_paths and str(path) in force_paths),
                )
            if allow_deletes:
                await self._process_pending_deletes(
                    task=task,
                    status=status,
                    drive_service=runtime.drive_service,
                )
        finally:
            await self._close_owned_services(runtime)

    async def _upload_with_guard(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        runtime: UploadRuntimeServices,
        force: bool,
    ) -> None:
        try:
            await self._upload_path(
                task,
                status,
                path,
                runtime.docx_service,
                runtime.file_uploader,
                runtime.drive_service,
                runtime.import_task_service,
                force=force,
            )
        except Exception as exc:
            status.failed_files += 1
            status.last_error = str(exc)
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=str(exc),
                ),
                None,
            )
            logger.error("上传失败: task_id={} path={} error={}", task.id, path, exc)

    @staticmethod
    async def _close_owned_services(runtime: UploadRuntimeServices) -> None:
        for service in runtime.owned_services:
            close = getattr(service, "close", None)
            if close:
                await close()


__all__ = ["SyncUploadOrchestrationService", "UploadRuntimeServices"]
