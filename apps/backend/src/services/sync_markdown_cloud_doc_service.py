from __future__ import annotations

import time
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger

from src.services.drive_service import DriveFile, DriveService
from src.services.file_uploader import FileUploader
from src.services.import_task_service import ImportTaskError, ImportTaskService
from src.services.sync_block_service import SyncBlockService
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem

ResolveCloudParent = Callable[[SyncTaskItem, Path, DriveService], Awaitable[str]]
FindExistingDocByName = Callable[..., Awaitable[str | None]]
WaitForImportedDoc = Callable[..., Awaitable[DriveFile | None]]
ListFolderTokens = Callable[[DriveService, str], Awaitable[set[str]]]
ListFilesAll = Callable[[DriveService, str], Awaitable[list[DriveFile]]]
GetLocalSignature = Callable[[Path], tuple[str, int, float] | None]
CalculateLocalResourceSignature = Callable[[str, Path], str | None]
BuildCloudRevision = Callable[..., str | None]
ParseMtime = Callable[[str | int | float | None], float]
ReleaseDocLock = Callable[[str], None]
RecordEvent = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]


class SyncMarkdownCloudDocService:
    def __init__(
        self,
        *,
        link_service: SyncLinkService,
        block_service: SyncBlockService,
        resolve_cloud_parent: ResolveCloudParent,
        find_existing_doc_by_name: FindExistingDocByName,
        wait_for_imported_doc: WaitForImportedDoc,
        list_folder_tokens: ListFolderTokens,
        list_files_all: ListFilesAll,
        get_local_signature: GetLocalSignature,
        calculate_local_resource_signature: CalculateLocalResourceSignature,
        build_cloud_revision: BuildCloudRevision,
        parse_mtime: ParseMtime,
        release_doc_lock: ReleaseDocLock,
    ) -> None:
        self._link_service = link_service
        self._block_service = block_service
        self._resolve_cloud_parent = resolve_cloud_parent
        self._find_existing_doc_by_name = find_existing_doc_by_name
        self._wait_for_imported_doc = wait_for_imported_doc
        self._list_folder_tokens = list_folder_tokens
        self._list_files_all = list_files_all
        self._get_local_signature = get_local_signature
        self._calculate_local_resource_signature = calculate_local_resource_signature
        self._build_cloud_revision = build_cloud_revision
        self._parse_mtime = parse_mtime
        self._release_doc_lock = release_doc_lock

    async def create_cloud_doc_for_markdown(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
        record_event: RecordEvent,
    ) -> tuple[SyncLinkItem | None, bool]:
        suffix = path.suffix.lower().lstrip(".")
        if not suffix:
            record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="Markdown 文件缺少扩展名",
                ),
                task,
            )
            return None, False

        parent_token = await self._resolve_cloud_parent(task, path, drive_service)
        existing_doc_token = await self._find_existing_doc_by_name(
            drive_service=drive_service,
            folder_token=parent_token,
            expected_name=path.stem,
        )
        if existing_doc_token:
            link = await self._link_service.upsert_link(
                local_path=str(path),
                cloud_token=existing_doc_token,
                cloud_type="docx",
                task_id=task.id,
                updated_at=0.0,
                cloud_parent_token=parent_token,
            )
            record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="linked",
                    message="复用云端同名文档",
                ),
                task,
            )
            return link, False

        record_event(
            status,
            SyncFileEvent(path=str(path), status="creating", message="创建云端文档"),
            task,
        )
        created_doc = await self.import_markdown_doc(
            task=task,
            status=status,
            path=path,
            parent_token=parent_token,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            record_event=record_event,
        )
        if not created_doc:
            return None, False

        local_signature = self._get_local_signature(path)
        cloud_mtime = self.resolve_created_doc_mtime(
            created_doc,
            local_signature[2] if local_signature else None,
            parse_mtime=self._parse_mtime,
        )
        resource_signature = self._calculate_local_resource_signature(
            path.read_text(encoding="utf-8"),
            path.parent,
        )
        cloud_revision = self._build_cloud_revision(created_doc.token, cloud_mtime)
        link = await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=created_doc.token,
            cloud_type="docx",
            task_id=task.id,
            updated_at=cloud_mtime,
            cloud_parent_token=parent_token,
            local_hash=local_signature[0] if local_signature else None,
            local_size=local_signature[1] if local_signature else None,
            local_mtime=local_signature[2] if local_signature else None,
            cloud_revision=cloud_revision,
            cloud_mtime=cloud_mtime,
            local_resource_signature=resource_signature,
            resource_sync_revision=cloud_revision,
        )
        record_event(
            status,
            SyncFileEvent(path=str(path), status="created", message="云端文档已创建"),
            task,
        )
        return link, True

    async def reimport_cloud_doc_for_markdown(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        old_link: SyncLinkItem,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
        record_event: RecordEvent,
    ) -> SyncLinkItem | None:
        parent_token = await self._resolve_cloud_parent(task, path, drive_service)
        record_event(
            status,
            SyncFileEvent(
                path=str(path),
                status="reimporting",
                message="检测到超限表格，改用导入重建",
            ),
            task,
        )
        created_doc = await self.import_markdown_doc(
            task=task,
            status=status,
            path=path,
            parent_token=parent_token,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            record_event=record_event,
        )
        if not created_doc:
            return None

        await self._block_service.replace_blocks(str(path), old_link.cloud_token, [])
        await self.cleanup_duplicate_docs_by_name(
            drive_service=drive_service,
            parent_token=parent_token,
            expected_name=path.stem,
            keep_token=created_doc.token,
            path=path,
        )
        local_signature = self._get_local_signature(path)
        cloud_mtime = self.resolve_created_doc_mtime(
            created_doc,
            local_signature[2] if local_signature else old_link.local_mtime,
            parse_mtime=self._parse_mtime,
        )
        resource_signature = self._calculate_local_resource_signature(
            path.read_text(encoding="utf-8"),
            path.parent,
        )
        cloud_revision = self._build_cloud_revision(created_doc.token, cloud_mtime)
        return await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=created_doc.token,
            cloud_type="docx",
            task_id=task.id,
            updated_at=cloud_mtime,
            cloud_parent_token=parent_token,
            local_hash=local_signature[0] if local_signature else old_link.local_hash,
            local_size=local_signature[1] if local_signature else old_link.local_size,
            local_mtime=local_signature[2] if local_signature else old_link.local_mtime,
            cloud_revision=cloud_revision,
            cloud_mtime=cloud_mtime,
            local_resource_signature=resource_signature,
            resource_sync_revision=cloud_revision,
        )

    async def import_markdown_doc(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        parent_token: str,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
        record_event: RecordEvent,
    ) -> DriveFile | None:
        suffix = path.suffix.lower().lstrip(".")
        if not suffix:
            record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="Markdown 文件缺少扩展名",
                ),
                task,
            )
            return None

        existing_tokens = await self._list_folder_tokens(drive_service, parent_token)
        source_file_token: str | None = None
        try:
            upload = await file_uploader.upload_file(
                file_path=path,
                parent_node=parent_token,
                parent_type="explorer",
                record_db=False,
            )
            source_file_token = upload.file_token
            await import_task_service.create_import_task(
                file_extension=suffix,
                file_token=upload.file_token,
                mount_key=parent_token,
                file_name=path.stem,
                doc_type="docx",
            )
        except ImportTaskError as exc:
            record_event(
                status,
                SyncFileEvent(path=str(path), status="failed", message=str(exc)),
                task,
            )
            await self.cleanup_import_source_file(
                drive_service=drive_service,
                source_file_token=source_file_token,
                task_id=task.id,
                parent_token=parent_token,
                source_name=path.name,
            )
            return None
        except Exception as exc:
            record_event(
                status,
                SyncFileEvent(path=str(path), status="failed", message=str(exc)),
                task,
            )
            await self.cleanup_import_source_file(
                drive_service=drive_service,
                source_file_token=source_file_token,
                task_id=task.id,
                parent_token=parent_token,
                source_name=path.name,
            )
            return None

        created_doc = await self._wait_for_imported_doc(
            drive_service=drive_service,
            folder_token=parent_token,
            expected_name=path.stem,
            existing_tokens=existing_tokens,
        )
        await self.cleanup_import_source_file(
            drive_service=drive_service,
            source_file_token=source_file_token,
            task_id=task.id,
            parent_token=parent_token,
            source_name=path.name,
        )
        if not created_doc:
            record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="导入任务完成但未找到新文档",
                ),
                task,
            )
            return None
        return created_doc

    async def cleanup_duplicate_docs_by_name(
        self,
        *,
        drive_service: DriveService,
        parent_token: str,
        expected_name: str,
        keep_token: str,
        path: Path,
    ) -> None:
        items = await self._list_files_all(drive_service, parent_token)
        for item in items:
            if item.type not in {"docx", "doc"}:
                continue
            if item.name != expected_name or item.token == keep_token:
                continue
            try:
                await drive_service.delete_file(item.token, item.type)
            except Exception:
                logger.warning(
                    "删除同名旧文档失败，保留新文档: keep_token={} stale_token={} path={}",
                    keep_token,
                    item.token,
                    path,
                )
                continue
            self._release_doc_lock(item.token)
            logger.info(
                "已清理同名旧文档: keep_token={} stale_token={} path={}",
                keep_token,
                item.token,
                path,
            )

    async def cleanup_import_source_file(
        self,
        *,
        drive_service: DriveService,
        source_file_token: str | None,
        task_id: str,
        parent_token: str,
        source_name: str,
    ) -> None:
        token = (source_file_token or "").strip()
        if not token:
            return
        delete_file = getattr(drive_service, "delete_file", None)
        if not callable(delete_file):
            return
        try:
            await delete_file(token, "file")
            logger.info(
                "清理导入源文件成功: task_id={} parent={} file={} token={}",
                task_id,
                parent_token,
                source_name,
                token,
            )
        except Exception as exc:
            logger.warning(
                "清理导入源文件失败: task_id={} parent={} file={} token={} error={}",
                task_id,
                parent_token,
                source_name,
                token,
                exc,
            )

    @staticmethod
    def resolve_created_doc_mtime(
        created_doc: DriveFile,
        fallback_local_mtime: float | None,
        *,
        parse_mtime: ParseMtime,
    ) -> float:
        modified_time = created_doc.modified_time
        if modified_time is not None:
            try:
                return parse_mtime(modified_time)
            except Exception:
                logger.warning(
                    "解析新建云端文档 modified_time 失败，改用本地/当前时间兜底: token={} modified_time={}",
                    created_doc.token,
                    modified_time,
                )
        return max(float(fallback_local_mtime or 0.0), time.time())


__all__ = ["SyncMarkdownCloudDocService"]
