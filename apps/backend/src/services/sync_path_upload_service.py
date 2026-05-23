from __future__ import annotations

import time
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger

from src.services.docx_service import DocxService
from src.services.drive_service import DriveService
from src.services.file_uploader import FileUploader
from src.services.import_task_service import ImportTaskService
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem

ShouldIgnorePathFn = Callable[[SyncTaskItem, Path], bool]
ShouldUploadMarkdownDocFn = Callable[[SyncTaskItem], bool]
UploadMarkdownFn = Callable[..., Awaitable[None]]
UploadFileFn = Callable[..., Awaitable[None]]
ResolveCloudParentFn = Callable[..., Awaitable[str]]
GetLocalSignatureFn = Callable[[Path], tuple[str, int, float] | None]
BuildCloudRevisionFn = Callable[[str, float, bool | None, bool | None], str | None]
ListFilesAllFn = Callable[..., Awaitable[list]]
RecordEventFn = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]


class SyncPathUploadService:
    def __init__(
        self,
        *,
        uploading_paths: set[str],
        link_service: SyncLinkService,
        should_ignore_path: ShouldIgnorePathFn,
        should_upload_markdown_doc: ShouldUploadMarkdownDocFn,
        upload_markdown: UploadMarkdownFn,
        upload_file_callback: UploadFileFn,
        resolve_cloud_parent: ResolveCloudParentFn,
        get_local_signature: GetLocalSignatureFn,
        build_cloud_revision: BuildCloudRevisionFn,
        list_files_all: ListFilesAllFn,
        record_event: RecordEventFn,
    ) -> None:
        self._uploading_paths = uploading_paths
        self._link_service = link_service
        self._should_ignore_path = should_ignore_path
        self._should_upload_markdown_doc = should_upload_markdown_doc
        self._upload_markdown = upload_markdown
        self._upload_file_callback = upload_file_callback
        self._resolve_cloud_parent = resolve_cloud_parent
        self._get_local_signature = get_local_signature
        self._build_cloud_revision = build_cloud_revision
        self._list_files_all = list_files_all
        self._record_event = record_event

    async def upload_path(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        docx_service: DocxService,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
        *,
        force: bool = False,
    ) -> None:
        key = str(path)
        if key in self._uploading_paths:
            status.skipped_files += 1
            self._record_event(
                status,
                SyncFileEvent(path=key, status="skipped", message="上传中，跳过重复触发"),
                None,
            )
            logger.info("重复上传触发，已跳过: task_id={} path={}", task.id, key)
            return
        self._uploading_paths.add(key)
        try:
            if self._should_ignore_path(task, path):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=key, status="skipped", message="忽略内部目录"),
                    None,
                )
                return
            if not path.exists() or not path.is_file():
                return
            suffix = path.suffix.lower()
            if suffix == ".md":
                if not self._should_upload_markdown_doc(task):
                    status.skipped_files += 1
                    self._record_event(
                        status,
                        SyncFileEvent(
                            path=key,
                            status="skipped",
                            message="当前 MD 模式为仅下载，跳过 MD 上传",
                        ),
                        None,
                    )
                    logger.info(
                        "跳过 MD 上传（md_sync_mode=download_only）: task_id={} path={}",
                        task.id,
                        path,
                    )
                    return
                await self._upload_markdown(
                    task,
                    status,
                    path,
                    docx_service,
                    file_uploader,
                    drive_service,
                    import_task_service,
                    force=force,
                )
                return
            await self._upload_file_callback(
                task,
                status,
                path,
                file_uploader,
                drive_service,
                force=force,
            )
        finally:
            self._uploading_paths.discard(key)

    async def upload_file(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService | None = None,
        *,
        force: bool = False,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        signature = self._get_local_signature(path)
        if not signature:
            status.failed_files += 1
            self._record_event(
                status,
                SyncFileEvent(path=str(path), status="failed", message="读取本地文件失败"),
                None,
            )
            return
        file_hash, file_size, file_mtime = signature
        if link:
            if (
                link.local_hash
                and link.local_hash == file_hash
                and (link.local_size is None or link.local_size == file_size)
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化"),
                    None,
                )
                return
            if (
                task.sync_mode != "upload_only"
                and not force
                and not link.local_hash
                and file_mtime <= (link.updated_at + 1.0)
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="本地未变更"),
                    None,
                )
                return
        if link and link.cloud_type != "file":
            status.failed_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持文件上传: {link.cloud_type}",
                ),
                None,
            )
            return

        if drive_service:
            parent_token = await self._resolve_cloud_parent(task, path, drive_service)
        else:
            parent_token = task.cloud_folder_token

        logger.info("上传文件: task_id={} path={} parent={}", task.id, path, parent_token)
        result = await file_uploader.upload_file(
            file_path=path,
            parent_node=parent_token,
            parent_type="explorer",
        )
        synced_at = time.time()
        await self.cleanup_replaced_cloud_files(
            path=path,
            new_token=result.file_token,
            parent_token=parent_token,
            previous_link=link,
            drive_service=drive_service,
        )
        await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=result.file_token,
            cloud_type="file",
            task_id=task.id,
            updated_at=synced_at,
            cloud_parent_token=parent_token,
            local_hash=file_hash,
            local_size=file_size,
            local_mtime=file_mtime,
            cloud_revision=self._build_cloud_revision(result.file_token, synced_at),
            cloud_mtime=synced_at,
        )
        status.completed_files += 1
        self._record_event(status, SyncFileEvent(path=str(path), status="uploaded"), None)

    async def cleanup_replaced_cloud_files(
        self,
        *,
        path: Path,
        new_token: str,
        parent_token: str,
        previous_link: SyncLinkItem | None,
        drive_service: DriveService | None,
    ) -> None:
        delete_file = getattr(drive_service, "delete_file", None) if drive_service else None
        if not callable(delete_file):
            return

        stale_tokens: list[str] = []
        seen_tokens: set[str] = set()

        def _append_stale(token: str | None) -> None:
            normalized = (token or "").strip()
            if not normalized or normalized == new_token or normalized in seen_tokens:
                return
            seen_tokens.add(normalized)
            stale_tokens.append(normalized)

        if previous_link and previous_link.cloud_type == "file":
            _append_stale(previous_link.cloud_token)

        if drive_service:
            try:
                existing = await self._list_files_all(drive_service, parent_token)
            except Exception:
                logger.warning(
                    "列出云端文件失败，跳过同名副本清理: parent={} path={}",
                    parent_token,
                    path,
                )
            else:
                for item in existing:
                    if item.type == "file" and item.name == path.name:
                        _append_stale(item.token)

        for token in stale_tokens:
            try:
                await delete_file(token, "file")
            except Exception:
                logger.warning("删除旧云端文件失败，保留最新映射: token={} path={}", token, path)


__all__ = ["SyncPathUploadService"]
