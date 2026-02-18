from __future__ import annotations

import asyncio
import difflib
import shutil
import time
from datetime import datetime
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable, Literal
from urllib.parse import parse_qs, urlparse

from loguru import logger

from src.core.config import ConfigManager, DeletePolicy
from src.services.bitable_service import BitableService
from src.services.docx_service import DocxService
from src.services.drive_service import DriveFile, DriveNode, DriveService
from src.services.sheet_service import SheetService
from src.services.file_downloader import FileDownloader
from src.services.file_hash import calculate_file_hash
from src.services.file_uploader import FileUploader
from src.services.file_writer import FileWriter
from src.services.markdown_blocks import hash_block, split_markdown_blocks
from src.services.path_sanitizer import sanitize_filename, sanitize_path_segment
from src.services.import_task_service import ImportTaskError, ImportTaskService
from src.services.export_task_service import ExportTaskError, ExportTaskResult, ExportTaskService
from src.services.sync_block_service import BlockStateItem, SyncBlockService
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_task_service import SyncTaskItem
from src.services.sync_tombstone_service import SyncTombstoneService
from src.services.transcoder import DocxTranscoder
from src.services.watcher import FileChangeEvent, WatcherService

SyncState = Literal["idle", "running", "success", "failed", "cancelled"]
SYNC_LOG_LIMIT = 200
_LEGACY_DOCX_PLACEHOLDER_MARKERS = (
    "sheet_token:",
    "内嵌表格（sheet_token:",
)
_LEGACY_DOCX_SCAN_BYTES = 262_144
_CLOUD_MD_MIRROR_FOLDER_NAME = "_LarkSync_MD_Mirror"
_CLOUD_MD_MIRROR_CACHE_PREFIX = "__md_mirror__"
_LOCAL_TRASH_DIR_NAME = ".larksync_trash"
_MD_SYNC_MODE_ENHANCED = "enhanced"
_MD_SYNC_MODE_DOWNLOAD_ONLY = "download_only"
_MD_SYNC_MODE_DOC_ONLY = "doc_only"
_MD_SYNC_MODE_VALUES = {
    _MD_SYNC_MODE_ENHANCED,
    _MD_SYNC_MODE_DOWNLOAD_ONLY,
    _MD_SYNC_MODE_DOC_ONLY,
}


@dataclass
class SyncFileEvent:
    path: str
    status: str
    message: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SyncTaskStatus:
    task_id: str
    state: SyncState = "idle"
    started_at: float | None = None
    finished_at: float | None = None
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    last_error: str | None = None
    last_files: list[SyncFileEvent] = field(default_factory=list)

    def record_event(self, event: SyncFileEvent, limit: int = SYNC_LOG_LIMIT) -> None:
        self.last_files.append(event)
        if len(self.last_files) > limit:
            self.last_files = self.last_files[-limit:]


@dataclass(frozen=True)
class DownloadCandidate:
    node: DriveNode
    relative_dir: Path
    effective_token: str
    effective_type: str
    target_dir: Path
    target_path: Path
    mtime: float
    export_sub_id: str | None = None


class SyncTaskRunner:
    def __init__(
        self,
        drive_service: DriveService | None = None,
        docx_service: DocxService | None = None,
        transcoder: DocxTranscoder | None = None,
        file_downloader: FileDownloader | None = None,
        file_uploader: FileUploader | None = None,
        file_writer: FileWriter | None = None,
        link_service: SyncLinkService | None = None,
        tombstone_service: SyncTombstoneService | None = None,
        sheet_service: SheetService | None = None,
        bitable_service: BitableService | None = None,
        import_task_service: ImportTaskService | None = None,
        export_task_service: ExportTaskService | None = None,
        event_store: SyncEventStore | None = None,
        import_poll_attempts: int = 10,
        import_poll_interval: float = 1.0,
        export_poll_attempts: int = 20,
        export_poll_interval: float = 1.0,
    ) -> None:
        self._drive_service = drive_service
        self._docx_service = docx_service
        self._transcoder = transcoder
        self._file_downloader = file_downloader
        self._file_uploader = file_uploader
        self._file_writer = file_writer or FileWriter()
        self._link_service = link_service or SyncLinkService()
        self._tombstone_service = tombstone_service or SyncTombstoneService()
        self._sheet_service = sheet_service
        self._bitable_service = bitable_service
        self._block_service = SyncBlockService()
        self._import_task_service = import_task_service
        self._export_task_service = export_task_service
        self._event_store = event_store or SyncEventStore()
        self._import_poll_attempts = max(1, import_poll_attempts)
        self._import_poll_interval = max(0.0, import_poll_interval)
        self._export_poll_attempts = max(1, export_poll_attempts)
        self._export_poll_interval = max(0.0, export_poll_interval)
        self._statuses: dict[str, SyncTaskStatus] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._watchers: dict[str, WatcherService] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._uploading_paths: set[str] = set()
        self._doc_locks: dict[str, asyncio.Lock] = {}
        self._pending_uploads: dict[str, set[str]] = {}
        self._running_tasks: set[str] = set()
        self._task_meta: dict[str, SyncTaskItem] = {}
        self._initial_upload_scanned: set[str] = set()
        # 缓存: (task_id, relative_dir_posix) -> cloud_folder_token
        self._cloud_folder_cache: dict[tuple[str, str], str] = {}

    def get_status(self, task_id: str) -> SyncTaskStatus:
        return self._statuses.get(task_id) or SyncTaskStatus(task_id=task_id)

    def list_statuses(self) -> dict[str, SyncTaskStatus]:
        return dict(self._statuses)

    def _record_event(
        self,
        status: SyncTaskStatus,
        event: SyncFileEvent,
        task: SyncTaskItem | None = None,
    ) -> None:
        status.record_event(event)
        task_info = task or self._task_meta.get(status.task_id)
        task_name = (
            task_info.name
            if task_info and task_info.name
            else (task_info.local_path if task_info else "未命名任务")
        )
        self._event_store.append(
            SyncEventRecord(
                timestamp=event.timestamp,
                task_id=status.task_id,
                task_name=task_name,
                status=event.status,
                path=event.path,
                message=event.message,
            )
        )

    def ensure_watcher(self, task: SyncTaskItem) -> None:
        self._ensure_watcher(task)

    def stop_watcher(self, task_id: str) -> None:
        self._stop_watcher(task_id)

    def start_task(self, task: SyncTaskItem) -> SyncTaskStatus:
        self._task_meta[task.id] = task
        current = self._statuses.get(task.id)
        if current and current.state == "running":
            return current
        if task.id in self._running_tasks:
            status = current or SyncTaskStatus(task_id=task.id)
            self._record_event(
                status,
                SyncFileEvent(
                    path=task.local_path,
                    status="skipped",
                    message="任务运行中，跳过重复启动",
                ),
                task,
            )
            return status
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(
            task,
            status,
            message=f"任务启动: mode={task.sync_mode} update={task.update_mode or 'auto'}",
        )
        self._running_tasks.add(task.id)
        if task.sync_mode in {"bidirectional", "upload_only"}:
            self._ensure_watcher(task)
        logger.info(
            "启动同步任务: id={} mode={} local={} cloud={}",
            task.id,
            task.sync_mode,
            task.local_path,
            task.cloud_folder_token,
        )
        self._tasks[task.id] = asyncio.create_task(self.run_task(task))
        return status

    def cancel_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        self._running_tasks.discard(task_id)
        self._stop_watcher(task_id)

    def queue_local_change(self, task_id: str, path: Path) -> None:
        pending = self._pending_uploads.setdefault(task_id, set())
        pending.add(str(path))

    async def run_scheduled_upload(self, task: SyncTaskItem) -> None:
        # 首次调度时，全量扫描本地目录，将没有 SyncLink 的文件加入待上传队列
        if task.id not in self._initial_upload_scanned:
            self._initial_upload_scanned.add(task.id)
            await self._scan_for_unlinked_files(task)

        pending = self._pending_uploads.get(task.id) or set()
        has_pending_tombstone = await self._has_pending_tombstones(task.id)
        if not pending and not has_pending_tombstone:
            return
        if task.id in self._running_tasks:
            return
        self._running_tasks.add(task.id)
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(task, status, message="周期上传触发")
        paths = [Path(path) for path in sorted(pending)]
        self._pending_uploads[task.id] = set()
        try:
            await self._run_upload_paths(task, status, paths)
            status.state = "failed" if status.failed_files > 0 else "success"
            status.finished_at = time.time()
        except Exception as exc:
            status.state = "failed"
            status.last_error = str(exc)
            status.finished_at = time.time()
        finally:
            self._record_event(
                status,
                SyncFileEvent(
                    path=task.local_path,
                    status=status.state,
                    message=(
                        f"完成: total={status.total_files} "
                        f"ok={status.completed_files} "
                        f"failed={status.failed_files} "
                        f"skipped={status.skipped_files}"
                    ),
                ),
                task,
            )
            self._running_tasks.discard(task.id)

    async def run_scheduled_download(self, task: SyncTaskItem) -> None:
        if task.id in self._running_tasks:
            return
        self._running_tasks.add(task.id)
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(task, status, message="定时下载触发")
        try:
            await self._run_download(task, status)
            status.state = "failed" if status.failed_files > 0 else "success"
            status.finished_at = time.time()
        except Exception as exc:
            status.state = "failed"
            status.last_error = str(exc)
            status.finished_at = time.time()
        finally:
            self._record_event(
                status,
                SyncFileEvent(
                    path=task.local_path,
                    status=status.state,
                    message=(
                        f"完成: total={status.total_files} "
                        f"ok={status.completed_files} "
                        f"failed={status.failed_files} "
                        f"skipped={status.skipped_files}"
                    ),
                ),
                task,
            )
            self._running_tasks.discard(task.id)

    def _reset_status(self, task: SyncTaskItem, status: SyncTaskStatus, message: str) -> None:
        status.state = "running"
        status.started_at = time.time()
        status.finished_at = None
        status.total_files = 0
        status.completed_files = 0
        status.failed_files = 0
        status.skipped_files = 0
        status.last_error = None
        status.last_files = []
        self._record_event(
            status,
            SyncFileEvent(
                path=task.local_path,
                status="started",
                message=message,
            ),
            task,
        )

    async def run_task(self, task: SyncTaskItem) -> None:
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        try:
            if task.sync_mode == "download_only":
                await self._run_download(task, status)
            elif task.sync_mode == "upload_only":
                await self._run_upload(task, status)
            elif task.sync_mode == "bidirectional":
                await self._run_download(task, status)
                await self._run_upload(task, status)
            else:
                status.state = "failed"
                status.last_error = f"未知同步模式: {task.sync_mode}"
                status.finished_at = time.time()
                return
            status.state = "failed" if status.failed_files > 0 else "success"
            status.finished_at = time.time()
        except asyncio.CancelledError:
            status.state = "cancelled"
            status.last_error = "任务已取消"
            status.finished_at = time.time()
        except Exception as exc:
            status.state = "failed"
            status.last_error = str(exc)
            status.finished_at = time.time()
        finally:
            if status.state == "cancelled":
                message = "任务已取消"
            else:
                message = (
                    f"完成: total={status.total_files} "
                    f"ok={status.completed_files} "
                    f"failed={status.failed_files} "
                    f"skipped={status.skipped_files}"
                )
            self._record_event(
                status,
                SyncFileEvent(
                    path=task.local_path,
                    status=status.state,
                    message=message,
                ),
                task,
            )
            self._tasks.pop(task.id, None)
            self._running_tasks.discard(task.id)

    async def _run_download(self, task: SyncTaskItem, status: SyncTaskStatus) -> None:
        self._task_meta[task.id] = task
        drive_service = self._drive_service or DriveService()
        docx_service = self._docx_service or DocxService()
        sheet_service = self._sheet_service or SheetService()
        transcoder = self._transcoder or DocxTranscoder(sheet_service=sheet_service)
        file_downloader = self._file_downloader or FileDownloader()
        file_uploader = self._file_uploader or FileUploader()
        export_task_service = self._export_task_service or ExportTaskService()
        bitable_service = self._bitable_service or BitableService()
        link_service = self._link_service
        owned_services = []
        if self._drive_service is None:
            owned_services.append(drive_service)
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._transcoder is None:
            owned_services.append(transcoder)
        if self._file_downloader is None:
            owned_services.append(file_downloader)
        if self._file_uploader is None:
            owned_services.append(file_uploader)
        if self._export_task_service is None:
            owned_services.append(export_task_service)
        if self._sheet_service is None and self._transcoder is not None:
            owned_services.append(sheet_service)
        if self._bitable_service is None:
            owned_services.append(bitable_service)

        try:
            tree = await drive_service.scan_folder(
                task.cloud_folder_token, name=task.name or "同步根目录"
            )
            files = list(_flatten_files(tree))
            logger.info(
                "下载阶段: task_id={} files={}", task.id, len(files)
            )
            link_map = _build_link_map(files, task.local_path)
            persisted_links = await link_service.list_by_task(task.id)
            link_map = _merge_synced_link_map(link_map, persisted_links)
            persisted_by_path = {item.local_path: item for item in persisted_links}
            candidates = [
                self._build_download_candidate(task, node, relative_dir)
                for node, relative_dir in files
            ]
            candidates = await self._hydrate_export_sub_ids(
                candidates,
                drive_service,
                sheet_service=sheet_service,
                bitable_service=bitable_service,
            )
            selected_candidates, duplicated_candidates = self._select_download_candidates(
                candidates,
                persisted_by_path,
            )
            known_cloud_tokens = {item.effective_token for item in selected_candidates}
            selected_cloud_paths = {str(item.target_path) for item in selected_candidates}
            await self._enqueue_cloud_missing_deletes(
                task=task,
                status=status,
                persisted_links=persisted_links,
                cloud_paths=selected_cloud_paths,
            )
            status.total_files = len(selected_candidates) + len(duplicated_candidates)

            for duplicated in duplicated_candidates:
                status.skipped_files += 1
                self._record_event(status, 
                    SyncFileEvent(
                        path=str(duplicated.target_path),
                        status="skipped",
                        message=(
                            "云端存在同名文件，已跳过重复项: "
                            f"type={duplicated.effective_type} token={duplicated.effective_token}"
                        ),
                    )
                )
                logger.info(
                    "跳过重复同名云端文件: task_id={} path={} type={} token={}",
                    task.id,
                    duplicated.target_path,
                    duplicated.effective_type,
                    duplicated.effective_token,
                )

            for candidate in selected_candidates:
                node = candidate.node
                effective_token = candidate.effective_token
                effective_type = candidate.effective_type
                target_dir = candidate.target_dir
                target_path = candidate.target_path
                mtime = candidate.mtime
                persisted = persisted_by_path.get(str(target_path))
                if self._should_skip_download_for_local_newer(
                    task=task,
                    local_path=target_path,
                    cloud_mtime=mtime,
                ):
                    status.skipped_files += 1
                    self._record_event(status, 
                        SyncFileEvent(
                            path=str(target_path),
                            status="skipped",
                            message="本地较新，跳过下载",
                        )
                    )
                    logger.info(
                        "检测到本地较新文件，跳过下载: task_id={} path={} cloud_mtime={} local_mtime={}",
                        task.id,
                        target_path,
                        mtime,
                        target_path.stat().st_mtime,
                    )
                    continue
                if self._should_skip_download_for_unchanged(
                    local_path=target_path,
                    cloud_mtime=mtime,
                    persisted=persisted,
                    effective_token=effective_token,
                    effective_type=effective_type,
                ):
                    status.skipped_files += 1
                    self._record_event(status, 
                        SyncFileEvent(
                            path=str(target_path),
                            status="skipped",
                            message="云端未更新，跳过下载",
                        )
                    )
                    logger.info(
                        "云端未更新，跳过下载: task_id={} path={} type={} token={} cloud_mtime={}",
                        task.id,
                        target_path,
                        effective_type,
                        effective_token,
                        mtime,
                    )
                    continue
                try:
                    if effective_type in {"docx", "doc"}:
                        markdown = await self._download_docx(
                            effective_token,
                            docx_service=docx_service,
                            transcoder=transcoder,
                            base_dir=target_dir,
                            link_map=link_map,
                        )
                        self._file_writer.write_markdown(target_path, markdown, mtime)
                        signature = self._get_local_signature(target_path)
                        await link_service.upsert_link(
                            local_path=str(target_path),
                            cloud_token=effective_token,
                            cloud_type=effective_type,
                            task_id=task.id,
                            updated_at=mtime,
                            cloud_parent_token=node.parent_token,
                            local_hash=signature[0] if signature else None,
                            local_size=signature[1] if signature else None,
                            local_mtime=signature[2] if signature else None,
                            cloud_revision=self._build_cloud_revision(effective_token, mtime),
                            cloud_mtime=mtime,
                        )
                        if task.sync_mode in {"bidirectional", "upload_only"} and (
                            (task.update_mode or "auto") != "full"
                        ):
                            await self._rebuild_block_state(
                                task=task,
                                docx_service=docx_service,
                                document_id=effective_token,
                                markdown=markdown,
                                base_path=target_dir.as_posix(),
                                file_path=target_path,
                                user_id_type="open_id",
                            )
                        if self._should_sync_md_cloud_mirror(task):
                            await self._sync_markdown_mirror_copy(
                                task=task,
                                status=status,
                                path=target_path,
                                file_uploader=file_uploader,
                                drive_service=drive_service,
                            )
                        self._silence_path(task.id, target_path)
                        status.completed_files += 1
                        self._record_event(status, 
                            SyncFileEvent(
                                path=str(target_path), status="downloaded"
                            )
                        )
                    elif effective_type in _EXPORT_EXTENSION_MAP:
                        export_extension = _EXPORT_EXTENSION_MAP[effective_type]
                        await self._download_exported_file(
                            export_task_service=export_task_service,
                            file_downloader=file_downloader,
                            file_token=effective_token,
                            file_type=effective_type,
                            target_path=target_path,
                            mtime=mtime,
                            export_extension=export_extension,
                            export_sub_id=candidate.export_sub_id,
                        )
                        signature = self._get_local_signature(target_path)
                        await link_service.upsert_link(
                            local_path=str(target_path),
                            cloud_token=effective_token,
                            cloud_type=effective_type,
                            task_id=task.id,
                            updated_at=mtime,
                            cloud_parent_token=node.parent_token,
                            local_hash=signature[0] if signature else None,
                            local_size=signature[1] if signature else None,
                            local_mtime=signature[2] if signature else None,
                            cloud_revision=self._build_cloud_revision(effective_token, mtime),
                            cloud_mtime=mtime,
                        )
                        self._silence_path(task.id, target_path)
                        status.completed_files += 1
                        self._record_event(status, 
                            SyncFileEvent(
                                path=str(target_path), status="downloaded"
                            )
                        )
                    elif effective_type == "file":
                        await file_downloader.download(
                            file_token=effective_token,
                            file_name=target_path.name,
                            target_dir=target_dir,
                            mtime=mtime,
                        )
                        signature = self._get_local_signature(target_path)
                        await link_service.upsert_link(
                            local_path=str(target_path),
                            cloud_token=effective_token,
                            cloud_type=effective_type,
                            task_id=task.id,
                            updated_at=mtime,
                            cloud_parent_token=node.parent_token,
                            local_hash=signature[0] if signature else None,
                            local_size=signature[1] if signature else None,
                            local_mtime=signature[2] if signature else None,
                            cloud_revision=self._build_cloud_revision(effective_token, mtime),
                            cloud_mtime=mtime,
                        )
                        self._silence_path(task.id, target_path)
                        status.completed_files += 1
                        self._record_event(status, 
                            SyncFileEvent(
                                path=str(target_path), status="downloaded"
                            )
                        )
                    else:
                        status.skipped_files += 1
                        self._record_event(status, 
                            SyncFileEvent(
                                path=str(target_path),
                                status="skipped",
                                message=f"暂不支持类型: {effective_type}",
                            )
                        )
                except Exception as exc:
                    status.failed_files += 1
                    status.last_error = str(exc)
                    self._record_event(status, 
                        SyncFileEvent(
                            path=str(target_path),
                            status="failed",
                            message=f"type={effective_type} token={effective_token} error={exc}",
                        )
                    )
                    logger.error(
                        "下载失败: task_id={} path={} type={} token={} error={}",
                        task.id,
                        target_path,
                        effective_type,
                        effective_token,
                        exc,
                    )
            await self._process_pending_deletes(
                task=task,
                status=status,
                drive_service=drive_service,
                known_cloud_tokens=known_cloud_tokens,
            )
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

    @staticmethod
    def _should_skip_download_for_local_newer(
        *,
        task: SyncTaskItem,
        local_path: Path,
        cloud_mtime: float,
    ) -> bool:
        if task.sync_mode != "bidirectional":
            return False
        if not local_path.exists() or not local_path.is_file():
            return False
        try:
            local_mtime = local_path.stat().st_mtime
        except OSError:
            return False
        return local_mtime > (cloud_mtime + 1.0)

    @staticmethod
    def _should_skip_download_for_unchanged(
        *,
        local_path: Path,
        cloud_mtime: float,
        persisted: SyncLinkItem | None,
        effective_token: str,
        effective_type: str,
    ) -> bool:
        if persisted is None:
            return False
        if persisted.cloud_token != effective_token:
            return False
        if not local_path.exists() or not local_path.is_file():
            return False
        if effective_type in {"doc", "docx"} and _contains_legacy_docx_placeholder(
            local_path
        ):
            return False
        if persisted.cloud_mtime is not None and persisted.cloud_mtime >= (cloud_mtime - 1.0):
            if persisted.local_hash:
                signature = SyncTaskRunner._get_local_signature(local_path)
                if not signature:
                    return False
                return signature[0] == persisted.local_hash
            return True
        if persisted.updated_at >= (cloud_mtime - 1.0):
            if persisted.local_hash:
                signature = SyncTaskRunner._get_local_signature(local_path)
                if not signature:
                    return False
                return signature[0] == persisted.local_hash
            return True
        return False

    @staticmethod
    def _build_download_candidate(
        task: SyncTaskItem,
        node: DriveNode,
        relative_dir: Path,
    ) -> DownloadCandidate:
        effective_token, effective_type = _resolve_target(node)
        target_dir = Path(task.local_path) / relative_dir
        if effective_type in {"docx", "doc"}:
            filename = _docx_filename(node.name)
        elif effective_type in _EXPORT_EXTENSION_MAP:
            filename = _export_filename(node.name, _EXPORT_EXTENSION_MAP[effective_type])
        else:
            filename = sanitize_filename(node.name)
        export_sub_id = _extract_export_sub_id(node.url, effective_type)
        target_path = target_dir / filename
        return DownloadCandidate(
            node=node,
            relative_dir=relative_dir,
            effective_token=effective_token,
            effective_type=effective_type,
            target_dir=target_dir,
            target_path=target_path,
            mtime=_parse_mtime(node.modified_time),
            export_sub_id=export_sub_id,
        )

    async def _hydrate_export_sub_ids(
        self,
        candidates: list[DownloadCandidate],
        drive_service: DriveService,
        *,
        sheet_service: SheetService | None = None,
        bitable_service: BitableService | None = None,
    ) -> list[DownloadCandidate]:
        pending: list[tuple[str, str]] = []
        for candidate in candidates:
            if candidate.effective_type in _EXPORT_EXTENSION_MAP and not candidate.export_sub_id:
                pending.append((candidate.effective_token, candidate.effective_type))
        if not pending:
            return candidates
        meta_map = {}
        batch_query = getattr(drive_service, "batch_query_metas", None)
        if batch_query is not None:
            try:
                meta_map = await batch_query(pending, with_url=True)
            except Exception as exc:
                logger.warning("补齐表格导出 sub_id 失败: {}", exc)
        enriched: list[DownloadCandidate] = []
        remaining: dict[tuple[str, str], list[int]] = {}
        for idx, candidate in enumerate(candidates):
            if candidate.effective_type in _EXPORT_EXTENSION_MAP and not candidate.export_sub_id:
                meta = meta_map.get(candidate.effective_token)
                url = getattr(meta, "url", None) if meta else None
                sub_id = _extract_export_sub_id(url, candidate.effective_type)
                if sub_id:
                    candidate = replace(candidate, export_sub_id=sub_id)
                else:
                    key = (candidate.effective_token, candidate.effective_type)
                    remaining.setdefault(key, []).append(idx)
            enriched.append(candidate)

        if not remaining:
            return enriched

        for (token, file_type), indices in remaining.items():
            if file_type == "sheet":
                if not sheet_service:
                    continue
                try:
                    sheet_ids = await sheet_service.list_sheet_ids(token)
                except Exception as exc:
                    logger.warning("获取 sheet 子表失败: token={} error={}", token, exc)
                    continue
                if not sheet_ids:
                    continue
                for idx in indices:
                    enriched[idx] = replace(enriched[idx], export_sub_id=sheet_ids[0])
                logger.info(
                    "补齐 sheet sub_id: token={} sheet_id={}",
                    token,
                    sheet_ids[0],
                )
            elif file_type == "bitable":
                if not bitable_service:
                    continue
                try:
                    table_ids = await bitable_service.list_table_ids(token)
                except Exception as exc:
                    logger.warning("获取 bitable 子表失败: token={} error={}", token, exc)
                    continue
                if not table_ids:
                    continue
                for idx in indices:
                    enriched[idx] = replace(enriched[idx], export_sub_id=table_ids[0])
                logger.info(
                    "补齐 bitable sub_id: token={} table_id={}",
                    token,
                    table_ids[0],
                )

        return enriched

    @staticmethod
    def _select_download_candidates(
        candidates: list[DownloadCandidate],
        persisted_by_path: dict[str, SyncLinkItem],
    ) -> tuple[list[DownloadCandidate], list[DownloadCandidate]]:
        selected: dict[str, DownloadCandidate] = {}
        duplicated: list[DownloadCandidate] = []
        for candidate in candidates:
            key = str(candidate.target_path).lower()
            current = selected.get(key)
            if current is None:
                selected[key] = candidate
                continue
            persisted = persisted_by_path.get(str(candidate.target_path))
            chosen = SyncTaskRunner._choose_download_candidate(
                current=current,
                candidate=candidate,
                persisted=persisted,
            )
            if chosen is candidate:
                duplicated.append(current)
                selected[key] = candidate
            else:
                duplicated.append(candidate)
        return list(selected.values()), duplicated

    @staticmethod
    def _choose_download_candidate(
        *,
        current: DownloadCandidate,
        candidate: DownloadCandidate,
        persisted: SyncLinkItem | None,
    ) -> DownloadCandidate:
        if persisted:
            current_match = current.effective_token == persisted.cloud_token
            candidate_match = candidate.effective_token == persisted.cloud_token
            if candidate_match and not current_match:
                return candidate
            if current_match and not candidate_match:
                return current
        if candidate.mtime > current.mtime:
            return candidate
        if candidate.mtime < current.mtime:
            return current
        type_priority = {
            "docx": 3,
            "doc": 3,
            "sheet": 2,
            "bitable": 2,
            "file": 2,
        }
        candidate_rank = type_priority.get(candidate.effective_type, 1)
        current_rank = type_priority.get(current.effective_type, 1)
        if candidate_rank > current_rank:
            return candidate
        return current

    async def _download_docx(
        self,
        document_id: str,
        *,
        docx_service: DocxService,
        transcoder: DocxTranscoder,
        base_dir: Path | None = None,
        link_map: dict[str, Path] | None = None,
    ) -> str:
        blocks = await docx_service.list_blocks(document_id)
        return await transcoder.to_markdown(
            document_id, blocks, base_dir=base_dir, link_map=link_map
        )

    async def _download_exported_file(
        self,
        *,
        export_task_service: ExportTaskService,
        file_downloader: FileDownloader,
        file_token: str,
        file_type: str,
        target_path: Path,
        mtime: float,
        export_extension: str,
        export_sub_id: str | None,
    ) -> None:
        attempts: list[str | None] = [None]
        if export_sub_id:
            attempts.append(export_sub_id)
        last_error: Exception | None = None
        last_sub_id: str | None = None
        for sub_id in attempts:
            last_sub_id = sub_id
            try:
                task = await export_task_service.create_export_task(
                    file_extension=export_extension,
                    file_token=file_token,
                    file_type=file_type,
                    sub_id=sub_id,
                )
                result = await self._wait_for_export_task(
                    export_task_service,
                    task.ticket,
                    file_token=file_token,
                )
                if not result.file_token:
                    raise RuntimeError("导出任务未返回文件 token")
                await file_downloader.download_exported_file(
                    file_token=result.file_token,
                    file_name=target_path.name,
                    target_dir=target_path.parent,
                    mtime=mtime,
                )
                return
            except (ExportTaskError, RuntimeError) as exc:
                last_error = exc
                if sub_id is None and export_sub_id:
                    logger.info(
                        "导出任务失败，尝试携带 sub_id 重试: token={} type={} sub_id={}",
                        file_token,
                        file_type,
                        export_sub_id,
                    )
                    continue
                break
        suffix = f" sub_id={last_sub_id}" if last_sub_id else ""
        raise RuntimeError(f"导出任务失败{suffix}: {last_error}") from last_error

    async def _wait_for_export_task(
        self,
        export_task_service: ExportTaskService,
        ticket: str,
        *,
        file_token: str | None = None,
    ) -> ExportTaskResult:
        last_error: str | None = None
        last_result: ExportTaskResult | None = None
        for attempt in range(self._export_poll_attempts):
            result = await export_task_service.get_export_task_result(
                ticket,
                file_token=file_token,
            )
            last_result = result
            job_status = result.job_status
            if job_status == 0:
                if result.file_token:
                    return result
                last_error = "导出任务未返回文件 token"
                break
            if result.job_error_msg:
                last_error = (
                    f"导出任务失败: status={job_status} msg={result.job_error_msg}"
                )
                break
            if job_status not in (None, 1, 2):
                last_error = f"导出任务失败: status={job_status}"
                break
            if attempt < self._export_poll_attempts - 1:
                await asyncio.sleep(self._export_poll_interval)
        if last_error:
            raise RuntimeError(last_error)
        if last_result and last_result.job_status not in (None, 1, 2):
            detail = f"导出任务失败: status={last_result.job_status}"
            if last_result.job_error_msg:
                detail = f"{detail} msg={last_result.job_error_msg}"
            raise RuntimeError(detail)
        status_hint = (
            f" status={last_result.job_status}"
            if last_result and last_result.job_status is not None
            else ""
        )
        raise RuntimeError(f"导出任务超时{status_hint}")

    async def _run_upload(self, task: SyncTaskItem, status: SyncTaskStatus) -> None:
        self._task_meta[task.id] = task
        docx_service = self._docx_service or DocxService()
        file_uploader = self._file_uploader or FileUploader()
        drive_service = self._drive_service or DriveService()
        import_task_service = self._import_task_service or ImportTaskService()
        owned_services = []
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._file_uploader is None:
            owned_services.append(file_uploader)
        if self._drive_service is None:
            owned_services.append(drive_service)
        if self._import_task_service is None:
            owned_services.append(import_task_service)

        try:
            if task.sync_mode == "upload_only":
                await self._prefill_links_from_cloud(task, drive_service)
            await self._enqueue_missing_local_deletes(task=task, status=status)
            files = list(self._iter_local_files(task))
            logger.info(
                "上传阶段: task_id={} files={}", task.id, len(files)
            )
            status.total_files += len(files)
            for path in files:
                try:
                    await self._upload_path(
                        task,
                        status,
                        path,
                        docx_service,
                        file_uploader,
                        drive_service,
                        import_task_service,
                    )
                except Exception as exc:
                    status.failed_files += 1
                    status.last_error = str(exc)
                    self._record_event(status, 
                        SyncFileEvent(
                            path=str(path),
                            status="failed",
                            message=str(exc),
                        )
                    )
                    logger.error(
                        "上传失败: task_id={} path={} error={}",
                        task.id,
                        path,
                        exc,
                    )
            await self._process_pending_deletes(
                task=task,
                status=status,
                drive_service=drive_service,
            )
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

    async def _run_upload_paths(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        paths: Iterable[Path],
    ) -> None:
        docx_service = self._docx_service or DocxService()
        file_uploader = self._file_uploader or FileUploader()
        drive_service = self._drive_service or DriveService()
        import_task_service = self._import_task_service or ImportTaskService()
        owned_services = []
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._file_uploader is None:
            owned_services.append(file_uploader)
        if self._drive_service is None:
            owned_services.append(drive_service)
        if self._import_task_service is None:
            owned_services.append(import_task_service)

        try:
            if task.sync_mode == "upload_only":
                await self._prefill_links_from_cloud(task, drive_service)
            await self._enqueue_missing_local_deletes(task=task, status=status)
            path_list = list(paths)
            status.total_files += len(path_list)
            for path in path_list:
                try:
                    await self._upload_path(
                        task,
                        status,
                        path,
                        docx_service,
                        file_uploader,
                        drive_service,
                        import_task_service,
                    )
                except Exception as exc:
                    status.failed_files += 1
                    status.last_error = str(exc)
                    self._record_event(status, 
                        SyncFileEvent(
                            path=str(path),
                            status="failed",
                            message=str(exc),
                        )
                    )
                    logger.error(
                        "上传失败: task_id={} path={} error={}",
                        task.id,
                        path,
                        exc,
                    )
            await self._process_pending_deletes(
                task=task,
                status=status,
                drive_service=drive_service,
            )
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

    async def _upload_path(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        docx_service: DocxService,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> None:
        key = str(path)
        if key in self._uploading_paths:
            status.skipped_files += 1
            self._record_event(status, 
                SyncFileEvent(path=key, status="skipped", message="上传中，跳过重复触发")
            )
            logger.info("重复上传触发，已跳过: task_id={} path={}", task.id, key)
            return
        self._uploading_paths.add(key)
        try:
            if self._should_ignore_path(task, path):
                status.skipped_files += 1
                self._record_event(status, 
                    SyncFileEvent(path=key, status="skipped", message="忽略内部目录")
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
                )
                return
            await self._upload_file(task, status, path, file_uploader, drive_service)
        finally:
            self._uploading_paths.discard(key)

    async def _upload_markdown(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        docx_service: DocxService,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        if link and link.cloud_type == "file":
            await self._upload_file(task, status, path, file_uploader, drive_service)
            return
        imported_doc = False
        if not link:
            link, imported_doc = await self._create_cloud_doc_for_markdown(
                task=task,
                status=status,
                path=path,
                file_uploader=file_uploader,
                drive_service=drive_service,
                import_task_service=import_task_service,
            )
            if not link:
                status.failed_files += 1
                self._record_event(status, 
                    SyncFileEvent(
                        path=str(path),
                        status="failed",
                        message="创建云端文档失败",
                    )
                )
                return
        base_path = path.parent.as_posix()
        mtime = path.stat().st_mtime
        file_hash = calculate_file_hash(path)
        block_states = await self._block_service.list_blocks(str(path), link.cloud_token)
        if block_states:
            if all(item.file_hash == file_hash for item in block_states):
                status.skipped_files += 1
                self._record_event(status, 
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化")
                )
                return
        else:
            if link.local_hash and link.local_hash == file_hash:
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化"),
                )
                return
            if task.sync_mode != "upload_only" and mtime <= (link.updated_at + 1.0):
                status.skipped_files += 1
                self._record_event(status, 
                    SyncFileEvent(path=str(path), status="skipped", message="本地未变更")
                )
                return
        update_mode = task.update_mode or "auto"
        if link.cloud_type not in {"docx", "doc"}:
            status.failed_files += 1
            self._record_event(status, 
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持 Markdown 覆盖: {link.cloud_type}",
                )
            )
            return
        if (not imported_doc) and (not block_states) and update_mode in {"auto", "partial"}:
            await self._bootstrap_block_state(
                path=path,
                cloud_token=link.cloud_token,
                docx_service=docx_service,
                status=status,
            )
        lock = self._doc_locks.setdefault(link.cloud_token, asyncio.Lock())
        async with lock:
            markdown = path.read_text(encoding="utf-8")
            logger.info(
                "上传文档: task_id={} path={} token={}",
                task.id,
                path,
                link.cloud_token,
            )
            if imported_doc:
                await self._rebuild_block_state(
                    task=task,
                    docx_service=docx_service,
                    document_id=link.cloud_token,
                    markdown=markdown,
                    base_path=base_path,
                    file_path=path,
                    user_id_type="open_id",
                )
            else:
                applied = False
                if update_mode in {"auto", "partial"}:
                    try:
                        applied = await self._apply_block_update(
                            task=task,
                            docx_service=docx_service,
                            document_id=link.cloud_token,
                            markdown=markdown,
                            base_path=base_path,
                            file_path=path,
                            status=status,
                            force=update_mode == "partial",
                        )
                    except RuntimeError:
                        if update_mode == "partial":
                            raise
                if not applied:
                    if update_mode == "partial":
                        raise RuntimeError("partial 模式要求块级更新，但未产生可应用差异")
                    await docx_service.replace_document_content(
                        link.cloud_token,
                        markdown,
                        base_path=base_path,
                        update_mode="full",
                    )
                    await self._rebuild_block_state(
                        task=task,
                        docx_service=docx_service,
                        document_id=link.cloud_token,
                        markdown=markdown,
                        base_path=base_path,
                        file_path=path,
                        user_id_type="open_id",
                    )
        synced_at = time.time()
        # 使用缓存获取 parent_token（已在 _create_cloud_doc_for_markdown 或更早处解析）
        upload_parent = await self._resolve_cloud_parent(task, path, drive_service)
        await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=link.cloud_token,
            cloud_type=link.cloud_type,
            task_id=task.id,
            updated_at=synced_at,
            cloud_parent_token=upload_parent,
            local_hash=file_hash,
            local_size=path.stat().st_size,
            local_mtime=path.stat().st_mtime,
            cloud_revision=self._build_cloud_revision(link.cloud_token, synced_at),
            cloud_mtime=synced_at,
        )
        if self._should_sync_md_cloud_mirror(task):
            await self._sync_markdown_mirror_copy(
                task=task,
                status=status,
                path=path,
                file_uploader=file_uploader,
                drive_service=drive_service,
            )
        else:
            await self._cleanup_md_mirror_copy(
                task=task,
                local_path=path,
                drive_service=drive_service,
            )
        status.completed_files += 1
        self._record_event(status, SyncFileEvent(path=str(path), status="uploaded"))
        logger.info("上传完成: task_id={} path={}", task.id, path)

    @staticmethod
    def _supports_md_cloud_mirror(drive_service: DriveService) -> bool:
        return callable(getattr(drive_service, "list_files", None)) and callable(
            getattr(drive_service, "create_folder", None)
        )

    def _resolve_md_sync_mode(self, task: SyncTaskItem) -> str:
        mode = (task.md_sync_mode or "").strip().lower()
        if mode in _MD_SYNC_MODE_VALUES:
            return mode
        cfg = ConfigManager.get().config
        return (
            _MD_SYNC_MODE_ENHANCED
            if bool(cfg.upload_md_to_cloud)
            else _MD_SYNC_MODE_DOWNLOAD_ONLY
        )

    def _should_upload_markdown_doc(self, task: SyncTaskItem) -> bool:
        return self._resolve_md_sync_mode(task) != _MD_SYNC_MODE_DOWNLOAD_ONLY

    def _should_sync_md_cloud_mirror(self, task: SyncTaskItem) -> bool:
        return self._resolve_md_sync_mode(task) == _MD_SYNC_MODE_ENHANCED

    async def _sync_markdown_mirror_copy(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService,
    ) -> None:
        if path.suffix.lower() != ".md":
            return
        if not self._supports_md_cloud_mirror(drive_service):
            return

        mirror_parent = await self._resolve_md_mirror_parent(
            task=task,
            path=path,
            drive_service=drive_service,
        )
        existing = await self._list_files_all(drive_service, mirror_parent)
        same_name_files = [
            item for item in existing if item.type == "file" and item.name == path.name
        ]
        delete_file = getattr(drive_service, "delete_file", None)
        if callable(delete_file):
            for item in same_name_files:
                try:
                    await delete_file(item.token, item.type)
                except Exception as exc:
                    logger.warning(
                        "删除旧的云端 MD 镜像失败，继续覆盖上传: token={} error={}",
                        item.token,
                        exc,
                    )
        elif same_name_files:
            logger.warning("当前 DriveService 不支持删除旧镜像，可能出现同名 MD 副本累积")

        await file_uploader.upload_file(
            file_path=path,
            parent_node=mirror_parent,
            parent_type="explorer",
            record_db=False,
        )
        self._record_event(
            status,
            SyncFileEvent(
                path=str(path),
                status="mirrored",
                message=f"MD 镜像已更新到云端目录：{_CLOUD_MD_MIRROR_FOLDER_NAME}",
            ),
            task,
        )

    @staticmethod
    def _normalize_delete_policy(raw_policy: object) -> DeletePolicy:
        if isinstance(raw_policy, DeletePolicy):
            return raw_policy
        try:
            return DeletePolicy(str(raw_policy))
        except ValueError:
            return DeletePolicy.safe

    def _resolve_delete_policy(self, task: SyncTaskItem | None = None) -> tuple[DeletePolicy, float]:
        config = ConfigManager.get().config
        policy_raw: object = config.delete_policy
        grace_raw: object = config.delete_grace_minutes
        if task is not None:
            if task.delete_policy:
                policy_raw = task.delete_policy
            if task.delete_grace_minutes is not None:
                grace_raw = task.delete_grace_minutes
        policy = self._normalize_delete_policy(policy_raw)
        grace_minutes = int(grace_raw or 0)
        if grace_minutes < 0:
            grace_minutes = 0
        grace_seconds = float(grace_minutes * 60)
        if policy == DeletePolicy.strict:
            grace_seconds = 0.0
        return policy, grace_seconds

    async def _has_pending_tombstones(self, task_id: str) -> bool:
        try:
            pending = await self._tombstone_service.list_pending(task_id)
        except Exception:
            logger.exception("读取删除墓碑失败: task_id={}", task_id)
            return False
        return bool(pending)

    @staticmethod
    def _build_cloud_revision(cloud_token: str, cloud_mtime: float | None) -> str | None:
        token = (cloud_token or "").strip()
        if not token:
            return None
        if cloud_mtime is None:
            return token
        return f"{token}@{int(cloud_mtime * 1000)}"

    @staticmethod
    def _get_local_signature(path: Path) -> tuple[str, int, float] | None:
        if not path.exists() or not path.is_file():
            return None
        try:
            stat = path.stat()
            file_hash = calculate_file_hash(path)
        except OSError:
            return None
        return file_hash, int(stat.st_size), float(stat.st_mtime)

    async def _enqueue_local_delete_tombstone(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        local_path: Path,
        reason: str,
    ) -> bool:
        policy, grace_seconds = self._resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return False
        link = await self._link_service.get_by_local_path(str(local_path))
        if not link:
            return False
        expire_at = time.time() + grace_seconds
        try:
            await self._tombstone_service.create_or_refresh(
                task_id=task.id,
                local_path=str(local_path),
                cloud_token=link.cloud_token,
                cloud_type=link.cloud_type,
                source="local",
                reason=reason,
                expire_at=expire_at,
            )
        except Exception:
            logger.exception(
                "写入本地删除墓碑失败: task_id={} path={}",
                task.id,
                local_path,
            )
            return False
        self._record_event(
            status,
            SyncFileEvent(
                path=str(local_path),
                status="delete_pending",
                message=f"{reason}，待处理删除同步",
            ),
            task,
        )
        return True

    async def _enqueue_missing_local_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
    ) -> None:
        policy, grace_seconds = self._resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return
        links = await self._link_service.list_by_task(task.id)
        if not links:
            return
        expire_at = time.time() + grace_seconds
        for link in links:
            local_path = Path(link.local_path)
            if local_path.exists():
                continue
            if link.updated_at <= 0 and not link.local_hash:
                # 仅云端预填映射、尚未建立本地基线时，不判定为“本地删除”。
                continue
            try:
                await self._tombstone_service.create_or_refresh(
                    task_id=task.id,
                    local_path=link.local_path,
                    cloud_token=link.cloud_token,
                    cloud_type=link.cloud_type,
                    source="local",
                    reason="检测到本地已删除",
                    expire_at=expire_at,
                )
            except Exception:
                logger.exception(
                    "写入本地删除墓碑失败: task_id={} path={}",
                    task.id,
                    link.local_path,
                )
                continue
            self._record_event(
                status,
                SyncFileEvent(
                    path=link.local_path,
                    status="delete_pending",
                    message="检测到本地已删除，待处理删除同步",
                ),
                task,
            )

    async def _enqueue_cloud_missing_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        persisted_links: list[SyncLinkItem],
        cloud_paths: set[str],
    ) -> None:
        policy, grace_seconds = self._resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return
        expire_at = time.time() + grace_seconds
        for link in persisted_links:
            if link.local_path in cloud_paths:
                continue
            try:
                await self._tombstone_service.create_or_refresh(
                    task_id=task.id,
                    local_path=link.local_path,
                    cloud_token=link.cloud_token,
                    cloud_type=link.cloud_type,
                    source="cloud",
                    reason="检测到云端已删除",
                    expire_at=expire_at,
                )
            except Exception:
                logger.exception(
                    "写入云端删除墓碑失败: task_id={} path={}",
                    task.id,
                    link.local_path,
                )
                continue
            self._record_event(
                status,
                SyncFileEvent(
                    path=link.local_path,
                    status="delete_pending",
                    message="检测到云端已删除，待处理本地删除",
                ),
                task,
            )

    async def _process_pending_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        drive_service: DriveService,
        known_cloud_tokens: set[str] | None = None,
    ) -> None:
        retry_delay_seconds = 300.0
        policy, _ = self._resolve_delete_policy(task)
        try:
            pending = await self._tombstone_service.list_pending(
                task.id,
                before=time.time(),
            )
        except Exception:
            logger.exception("查询待处理删除墓碑失败: task_id={}", task.id)
            return
        if not pending:
            return
        if policy == DeletePolicy.off:
            for tombstone in pending:
                await self._tombstone_service.mark_status(
                    tombstone.id,
                    status="cancelled",
                    reason="删除同步已关闭",
                )
            return

        delete_file = getattr(drive_service, "delete_file", None)
        for tombstone in pending:
            local_path = Path(tombstone.local_path)
            try:
                if tombstone.source == "local":
                    if local_path.exists():
                        await self._tombstone_service.mark_status(
                            tombstone.id,
                            status="cancelled",
                            reason="本地文件已恢复",
                        )
                        continue
                    if tombstone.cloud_token:
                        if not callable(delete_file):
                            await self._tombstone_service.mark_status(
                                tombstone.id,
                                status="failed",
                                reason="当前 DriveService 不支持云端删除",
                                expire_at=time.time() + retry_delay_seconds,
                            )
                            self._record_event(
                                status,
                                SyncFileEvent(
                                    path=tombstone.local_path,
                                    status="delete_failed",
                                    message="云端删除失败：当前 DriveService 不支持删除接口",
                                ),
                                task,
                            )
                            continue
                        try:
                            await delete_file(tombstone.cloud_token, tombstone.cloud_type)
                        except Exception as exc:
                            if self._is_cloud_already_deleted_error(exc):
                                logger.info(
                                    "云端文件已不存在，按幂等成功处理: token={} type={} path={}",
                                    tombstone.cloud_token,
                                    tombstone.cloud_type,
                                    tombstone.local_path,
                                )
                            else:
                                raise
                    await self._cleanup_md_mirror_copy(
                        task=task,
                        local_path=local_path,
                        drive_service=drive_service,
                    )
                    await self._cleanup_deleted_state(
                        local_path=tombstone.local_path,
                        cloud_token=tombstone.cloud_token,
                    )
                    await self._tombstone_service.mark_status(
                        tombstone.id,
                        status="executed",
                    )
                    self._record_event(
                        status,
                        SyncFileEvent(
                            path=tombstone.local_path,
                            status="deleted",
                            message="已删除云端文件并清理映射",
                        ),
                        task,
                    )
                    continue

                if known_cloud_tokens and tombstone.cloud_token:
                    if tombstone.cloud_token in known_cloud_tokens:
                        await self._tombstone_service.mark_status(
                            tombstone.id,
                            status="cancelled",
                            reason="云端文件已恢复",
                        )
                        continue

                await self._cleanup_md_mirror_copy(
                    task=task,
                    local_path=local_path,
                    drive_service=drive_service,
                )

                if local_path.exists():
                    if policy == DeletePolicy.strict:
                        if local_path.is_dir():
                            shutil.rmtree(local_path, ignore_errors=True)
                        else:
                            local_path.unlink(missing_ok=True)
                        local_message = "本地文件已删除"
                    else:
                        moved_to = self._move_to_local_trash(task, local_path)
                        local_message = f"本地文件已移入回收目录: {moved_to}"
                else:
                    local_message = "本地文件已不存在"

                await self._cleanup_deleted_state(
                    local_path=tombstone.local_path,
                    cloud_token=tombstone.cloud_token,
                )
                await self._tombstone_service.mark_status(
                    tombstone.id,
                    status="executed",
                )
                self._record_event(
                    status,
                    SyncFileEvent(
                        path=tombstone.local_path,
                        status="deleted",
                        message=local_message,
                    ),
                    task,
                )
            except Exception as exc:
                await self._tombstone_service.mark_status(
                    tombstone.id,
                    status="failed",
                    reason=str(exc),
                    expire_at=time.time() + retry_delay_seconds,
                )
                self._record_event(
                    status,
                    SyncFileEvent(
                        path=tombstone.local_path,
                        status="delete_failed",
                        message=str(exc),
                    ),
                    task,
                )
                logger.warning(
                    "处理删除墓碑失败: task_id={} source={} path={} error={}",
                    task.id,
                    tombstone.source,
                    tombstone.local_path,
                    exc,
                )

    async def _cleanup_deleted_state(
        self,
        *,
        local_path: str,
        cloud_token: str | None,
    ) -> None:
        link = await self._link_service.get_by_local_path(local_path)
        token = cloud_token or (link.cloud_token if link else None)
        try:
            await self._link_service.delete_by_local_path(local_path)
        except Exception:
            logger.exception("清理同步映射失败: {}", local_path)
        if token:
            try:
                await self._block_service.replace_blocks(local_path, token, [])
            except Exception:
                logger.exception("清理块级映射失败: path={} token={}", local_path, token)

    @staticmethod
    def _move_to_local_trash(task: SyncTaskItem, local_path: Path) -> Path:
        root = Path(task.local_path)
        trash_root = root / _LOCAL_TRASH_DIR_NAME
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            relative = local_path.relative_to(root)
        except ValueError:
            relative = Path(local_path.name)
        candidate = trash_root / timestamp / relative
        candidate.parent.mkdir(parents=True, exist_ok=True)
        target = candidate
        if target.exists():
            index = 1
            while True:
                if target.suffix:
                    name = f"{target.stem}.{index}{target.suffix}"
                else:
                    name = f"{target.name}.{index}"
                alt = target.with_name(name)
                if not alt.exists():
                    target = alt
                    break
                index += 1
        shutil.move(str(local_path), str(target))
        return target

    @staticmethod
    def _is_cloud_already_deleted_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = (
            "file has been delete",
            "file already deleted",
            "file not found",
            "resource not found",
            "not exist",
        )
        return any(marker in lowered for marker in markers)

    async def _cleanup_md_mirror_copy(
        self,
        *,
        task: SyncTaskItem,
        local_path: Path,
        drive_service: DriveService,
    ) -> None:
        if local_path.suffix.lower() != ".md":
            return
        if not self._supports_md_cloud_mirror(drive_service):
            return
        delete_file = getattr(drive_service, "delete_file", None)
        if not callable(delete_file):
            return
        mirror_parent = await self._find_md_mirror_parent_no_create(
            task=task,
            path=local_path,
            drive_service=drive_service,
        )
        if not mirror_parent:
            return
        existing = await self._list_files_all(drive_service, mirror_parent)
        for item in existing:
            if item.type != "file" or item.name != local_path.name:
                continue
            try:
                await delete_file(item.token, item.type)
            except Exception as exc:
                if self._is_cloud_already_deleted_error(exc):
                    continue
                logger.warning(
                    "删除云端 MD 镜像失败: task_id={} path={} token={} error={}",
                    task.id,
                    local_path,
                    item.token,
                    exc,
                )

    async def _find_md_mirror_parent_no_create(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str | None:
        root_token = await self._find_md_mirror_root_no_create(task, drive_service)
        if not root_token:
            return None
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return root_token

        parent_parts = relative.parent.parts
        if not parent_parts or parent_parts == (".",):
            return root_token

        current_token = root_token
        accumulated = ""
        for part in parent_parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            cache_key = (task.id, f"{_CLOUD_MD_MIRROR_CACHE_PREFIX}/{accumulated}")
            cached = self._cloud_folder_cache.get(cache_key)
            if cached:
                current_token = cached
                continue
            existing_token = await self._find_subfolder(drive_service, current_token, part)
            if not existing_token:
                return None
            self._cloud_folder_cache[cache_key] = existing_token
            current_token = existing_token
        return current_token

    async def _find_md_mirror_root_no_create(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str | None:
        cache_key = (task.id, f"{_CLOUD_MD_MIRROR_CACHE_PREFIX}/root")
        cached = self._cloud_folder_cache.get(cache_key)
        if cached:
            return cached
        existing = await self._find_subfolder(
            drive_service, task.cloud_folder_token, _CLOUD_MD_MIRROR_FOLDER_NAME
        )
        if not existing:
            return None
        self._cloud_folder_cache[cache_key] = existing
        return existing

    async def _resolve_md_mirror_parent(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        root_token = await self._ensure_md_mirror_root(task, drive_service)
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return root_token

        parent_parts = relative.parent.parts
        if not parent_parts or parent_parts == (".",):
            return root_token

        current_token = root_token
        accumulated = ""
        for part in parent_parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            cache_key = (task.id, f"{_CLOUD_MD_MIRROR_CACHE_PREFIX}/{accumulated}")
            if cache_key in self._cloud_folder_cache:
                current_token = self._cloud_folder_cache[cache_key]
                continue
            existing_token = await self._find_subfolder(drive_service, current_token, part)
            if existing_token:
                self._cloud_folder_cache[cache_key] = existing_token
                current_token = existing_token
                continue
            new_token = await drive_service.create_folder(current_token, part)
            self._cloud_folder_cache[cache_key] = new_token
            current_token = new_token
            logger.info(
                "创建云端 MD 镜像子目录: task_id={} path={} token={}",
                task.id,
                accumulated,
                new_token,
            )
        return current_token

    async def _ensure_md_mirror_root(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str:
        cache_key = (task.id, f"{_CLOUD_MD_MIRROR_CACHE_PREFIX}/root")
        cached = self._cloud_folder_cache.get(cache_key)
        if cached:
            return cached
        existing = await self._find_subfolder(
            drive_service, task.cloud_folder_token, _CLOUD_MD_MIRROR_FOLDER_NAME
        )
        if existing:
            self._cloud_folder_cache[cache_key] = existing
            return existing
        created = await drive_service.create_folder(
            task.cloud_folder_token, _CLOUD_MD_MIRROR_FOLDER_NAME
        )
        self._cloud_folder_cache[cache_key] = created
        logger.info(
            "创建云端 MD 镜像根目录: task_id={} token={}",
            task.id,
            created,
        )
        return created

    async def _upload_file(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService | None = None,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        signature = self._get_local_signature(path)
        if not signature:
            status.failed_files += 1
            self._record_event(
                status,
                SyncFileEvent(path=str(path), status="failed", message="读取本地文件失败"),
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
                )
                return
            if (
                task.sync_mode != "upload_only"
                and not link.local_hash
                and file_mtime <= (link.updated_at + 1.0)
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="本地未变更"),
                )
                return
        if link and link.cloud_type != "file":
            status.failed_files += 1
            self._record_event(status, 
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持文件上传: {link.cloud_type}",
                )
            )
            return

        # 根据本地子目录结构解析正确的云端父文件夹
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
        self._record_event(status, SyncFileEvent(path=str(path), status="uploaded"))

    async def _bootstrap_block_state(
        self,
        *,
        path: Path,
        cloud_token: str,
        docx_service: DocxService,
        status: SyncTaskStatus,
        children_count: int | None = None,
    ) -> None:
        if children_count is None:
            root_block, _ = await docx_service.get_root_block(cloud_token)
            children_count = len(root_block.get("children") or [])
        now = time.time()
        await self._block_service.replace_blocks(
            str(path),
            cloud_token,
            [
                BlockStateItem(
                    file_hash="__bootstrap__",
                    local_path=str(path),
                    cloud_token=cloud_token,
                    block_index=0,
                    block_hash=f"__bootstrap__:{children_count}",
                    block_count=children_count,
                    updated_at=now,
                    created_at=now,
                )
            ],
        )
        self._record_event(status, 
            SyncFileEvent(
                path=str(path),
                status="bootstrapped",
                message=f"缺少块级状态，已自动初始化（children={children_count}）",
            )
        )
        logger.info(
            "块级状态自动初始化: path={} token={} children={}",
            path,
            cloud_token,
            children_count,
        )

    async def _create_cloud_doc_for_markdown(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> tuple[SyncLinkItem | None, bool]:
        suffix = path.suffix.lower().lstrip(".")
        if not suffix:
            self._record_event(status, 
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="Markdown 文件缺少扩展名",
                )
            )
            return None, False

        # 根据本地子目录结构解析正确的云端父文件夹
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
            self._record_event(status, 
                SyncFileEvent(
                    path=str(path),
                    status="linked",
                    message="复用云端同名文档",
                )
            )
            return link, False
        self._record_event(status, 
            SyncFileEvent(path=str(path), status="creating", message="创建云端文档")
        )
        existing_tokens = await self._list_folder_tokens(
            drive_service, parent_token
        )
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
            self._record_event(status, 
                SyncFileEvent(path=str(path), status="failed", message=str(exc))
            )
            await self._cleanup_import_source_file(
                drive_service=drive_service,
                source_file_token=source_file_token,
                task_id=task.id,
                parent_token=parent_token,
                source_name=path.name,
            )
            return None, False
        except Exception as exc:
            self._record_event(status, 
                SyncFileEvent(path=str(path), status="failed", message=str(exc))
            )
            await self._cleanup_import_source_file(
                drive_service=drive_service,
                source_file_token=source_file_token,
                task_id=task.id,
                parent_token=parent_token,
                source_name=path.name,
            )
            return None, False

        doc_token = await self._wait_for_imported_doc(
            drive_service=drive_service,
            folder_token=parent_token,
            expected_name=path.stem,
            existing_tokens=existing_tokens,
        )
        await self._cleanup_import_source_file(
            drive_service=drive_service,
            source_file_token=source_file_token,
            task_id=task.id,
            parent_token=parent_token,
            source_name=path.name,
        )
        if not doc_token:
            self._record_event(status, 
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="导入任务完成但未找到新文档",
                )
            )
            return None, False

        link = await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=doc_token,
            cloud_type="docx",
            task_id=task.id,
            updated_at=0.0,
            cloud_parent_token=parent_token,
        )
        self._record_event(status, 
            SyncFileEvent(path=str(path), status="created", message="云端文档已创建")
        )
        return link, True

    async def _cleanup_import_source_file(
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

    def _iter_local_files(self, task: SyncTaskItem) -> Iterable[Path]:
        root = Path(task.local_path)
        if not root.exists():
            return []
        return [path for path in root.rglob("*") if path.is_file()]

    async def _scan_for_unlinked_files(self, task: SyncTaskItem) -> int:
        """全量扫描本地目录，将没有 SyncLink 的文件加入待上传队列。

        用于覆盖以下场景：
        - 文件在 watcher 启动前就已存在（如从 download_only 切换到 bidirectional）
        - watcher 遗漏的文件事件
        """
        root = Path(task.local_path)
        if not root.exists():
            return 0

        skip_md = not self._should_upload_markdown_doc(task)

        queued = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if self._should_ignore_path(task, path):
                continue
            if skip_md and path.suffix.lower() == ".md":
                continue
            link = await self._link_service.get_by_local_path(str(path))
            if not link:
                self.queue_local_change(task.id, path)
                queued += 1
        if queued:
            logger.info(
                "初始扫描发现 {} 个未同步本地文件: task_id={}", queued, task.id
            )
        return queued

    def _should_ignore_path(self, task: SyncTaskItem, path: Path) -> bool:
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return True
        lowered = {part.lower() for part in relative.parts}
        if (
            "assets" in lowered
            or "attachments" in lowered
            or _LOCAL_TRASH_DIR_NAME.lower() in lowered
            or _CLOUD_MD_MIRROR_FOLDER_NAME.lower() in lowered
        ):
            return True
        return False

    async def _resolve_cloud_parent(
        self,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        """根据本地文件的相对路径，在云端逐层查找/创建对应的子文件夹。

        返回该文件应上传到的云端父文件夹 token。
        例如：本地 ``sync_root/sub1/sub2/doc.md`` → 云端 ``cloud_root/sub1/sub2`` 的 token。
        """
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return task.cloud_folder_token

        parent_parts = relative.parent.parts  # ('sub1', 'sub2') 或 ()
        if not parent_parts or parent_parts == (".",):
            return task.cloud_folder_token  # 文件在根目录

        current_token = task.cloud_folder_token
        accumulated = ""

        for part in parent_parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            cache_key = (task.id, accumulated)

            if cache_key in self._cloud_folder_cache:
                current_token = self._cloud_folder_cache[cache_key]
                continue

            # 先查找已有的同名子文件夹
            existing_token = await self._find_subfolder(
                drive_service, current_token, part
            )
            if existing_token:
                self._cloud_folder_cache[cache_key] = existing_token
                current_token = existing_token
            else:
                # 不存在则创建
                new_token = await drive_service.create_folder(current_token, part)
                self._cloud_folder_cache[cache_key] = new_token
                current_token = new_token
                logger.info(
                    "创建云端子文件夹: task_id={} path={} token={}",
                    task.id, accumulated, new_token,
                )

        return current_token

    async def _find_subfolder(
        self,
        drive_service: DriveService,
        parent_token: str,
        name: str,
    ) -> str | None:
        """在指定云端文件夹中按名称查找子文件夹。"""
        expected_name = (name or "").strip().lower()
        page_token: str | None = None
        while True:
            result = await drive_service.list_files(
                parent_token, page_token=page_token
            )
            for f in result.files:
                if f.type == "folder" and (f.name or "").strip().lower() == expected_name:
                    return f.token
            if not result.has_more or not result.next_page_token:
                break
            page_token = result.next_page_token
        return None

    def _ensure_watcher(self, task: SyncTaskItem) -> None:
        if task.id in self._watchers:
            return
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
        loop = self._loop
        if loop is None:
            return

        def _on_event(event: FileChangeEvent) -> None:
            asyncio.run_coroutine_threadsafe(
                self._handle_local_event(task, event), loop
            )

        watcher = WatcherService(Path(task.local_path), on_event=_on_event)
        watcher.start()
        self._watchers[task.id] = watcher

    def _stop_watcher(self, task_id: str) -> None:
        watcher = self._watchers.pop(task_id, None)
        if watcher:
            watcher.stop()
        self._initial_upload_scanned.discard(task_id)

    def _silence_path(self, task_id: str, path: Path) -> None:
        watcher = self._watchers.get(task_id)
        if watcher:
            watcher.silence(path)

    async def _list_folder_tokens(
        self, drive_service: DriveService, folder_token: str
    ) -> set[str]:
        items = await self._list_files_all(drive_service, folder_token)
        return {item.token for item in items}

    async def _list_files_all(
        self, drive_service: DriveService, folder_token: str
    ) -> list[DriveFile]:
        files: list[DriveFile] = []
        page_token: str | None = None
        while True:
            result = await drive_service.list_files(folder_token, page_token=page_token)
            files.extend(result.files)
            if not result.has_more or not result.next_page_token:
                break
            page_token = result.next_page_token
        return files

    async def _find_existing_doc_by_name(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
    ) -> str | None:
        items = await self._list_files_all(drive_service, folder_token)
        matched = [
            item
            for item in items
            if item.type in {"docx", "doc"} and item.name == expected_name
        ]
        if not matched:
            return None
        matched.sort(key=lambda item: _parse_mtime(item.modified_time), reverse=True)
        return matched[0].token

    async def _wait_for_imported_doc(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
        existing_tokens: set[str],
    ) -> str | None:
        for attempt in range(self._import_poll_attempts):
            items = await self._list_files_all(drive_service, folder_token)
            for item in items:
                if (
                    item.name == expected_name
                    and item.type in {"docx", "doc"}
                    and item.token not in existing_tokens
                ):
                    return item.token
            if attempt < self._import_poll_attempts - 1:
                await asyncio.sleep(self._import_poll_interval)
        return None

    async def _handle_local_event(self, task: SyncTaskItem, event: FileChangeEvent) -> None:
        if task.sync_mode == "download_only":
            return
        path = Path(event.dest_path or event.src_path)
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        if self._should_ignore_path(task, path):
            return
        if event.event_type == "deleted":
            marked = await self._enqueue_local_delete_tombstone(
                task=task,
                status=status,
                local_path=path,
                reason="监听到本地删除事件",
            )
            policy, _ = self._resolve_delete_policy(task)
            if marked and policy == DeletePolicy.strict:
                drive_service = self._drive_service or DriveService()
                should_close = self._drive_service is None
                try:
                    await self._process_pending_deletes(
                        task=task,
                        status=status,
                        drive_service=drive_service,
                    )
                finally:
                    if should_close:
                        await drive_service.close()
            return
        self.queue_local_change(task.id, path)
        self._record_event(
            status,
            SyncFileEvent(path=str(path), status="queued", message="等待周期上传"),
            task,
        )

    async def _apply_block_update(
        self,
        *,
        task: SyncTaskItem,
        docx_service: DocxService,
        document_id: str,
        markdown: str,
        base_path: str,
        file_path: Path,
        status: SyncTaskStatus,
        force: bool,
    ) -> bool:
        blocks = split_markdown_blocks(markdown)
        if not blocks:
            return False
        file_hash = calculate_file_hash(file_path)
        block_hashes = [hash_block(block) for block in blocks]
        existing = await self._block_service.list_blocks(str(file_path), document_id)
        if not existing:
            if force:
                raise RuntimeError("缺少块级状态，无法局部更新")
            return False
        total_existing = sum(item.block_count for item in existing)
        root_block, _ = await docx_service.get_root_block(document_id)
        root_children = root_block.get("children") or []
        if total_existing != len(root_children):
            if force:
                await self._bootstrap_block_state(
                    path=file_path,
                    cloud_token=document_id,
                    docx_service=docx_service,
                    status=status,
                    children_count=len(root_children),
                )
                existing = await self._block_service.list_blocks(
                    str(file_path), document_id
                )
                total_existing = sum(item.block_count for item in existing)
                if total_existing != len(root_children):
                    raise RuntimeError("块级映射不一致，无法局部更新")
            else:
                logger.info("块级更新跳过: 映射数量不一致")
                return False

        matcher = difflib.SequenceMatcher(
            a=[item.block_hash for item in existing], b=block_hashes
        )
        opcodes = matcher.get_opcodes()
        if not opcodes:
            return False

        now = time.time()
        counts = [item.block_count for item in existing]
        new_states: list[BlockStateItem] = list(existing)
        offset_blocks = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            start_block = i1 + offset_blocks
            end_block = i2 + offset_blocks
            start_index = sum(counts[:start_block])
            end_index = sum(counts[:end_block])
            if tag == "delete":
                if end_index > start_index:
                    await docx_service.delete_children(
                        document_id=document_id,
                        block_id=root_block["block_id"],
                        start_index=start_index,
                        end_index=end_index,
                    )
                    del counts[start_block:end_block]
                    del new_states[start_block:end_block]
                offset_blocks -= (i2 - i1)
                continue
            if tag == "insert":
                if j2 <= j1:
                    continue
                insert_index = start_index
                insert_items: list[BlockStateItem] = []
                for block in blocks[j1:j2]:
                    count = await docx_service.insert_markdown_block(
                        document_id=document_id,
                        root_block_id=root_block["block_id"],
                        markdown=block,
                        base_path=base_path,
                        user_id_type="open_id",
                        insert_index=insert_index,
                    )
                    insert_index += count
                    insert_items.append(
                        BlockStateItem(
                            file_hash=file_hash,
                            local_path=str(file_path),
                            cloud_token=document_id,
                            block_index=0,
                            block_hash=hash_block(block),
                            block_count=count,
                            updated_at=now,
                            created_at=now,
                        )
                    )
                counts[start_block:start_block] = [item.block_count for item in insert_items]
                new_states[start_block:start_block] = insert_items
                offset_blocks += (j2 - j1)
                continue
            if tag == "replace":
                if j2 <= j1 and end_index <= start_index:
                    continue
                insert_index = start_index
                insert_items: list[BlockStateItem] = []
                for block in blocks[j1:j2]:
                    count = await docx_service.insert_markdown_block(
                        document_id=document_id,
                        root_block_id=root_block["block_id"],
                        markdown=block,
                        base_path=base_path,
                        user_id_type="open_id",
                        insert_index=insert_index,
                    )
                    insert_index += count
                    insert_items.append(
                        BlockStateItem(
                            file_hash=file_hash,
                            local_path=str(file_path),
                            cloud_token=document_id,
                            block_index=0,
                            block_hash=hash_block(block),
                            block_count=count,
                            updated_at=now,
                            created_at=now,
                        )
                    )
                inserted_count = sum(item.block_count for item in insert_items)
                if end_index > start_index:
                    await docx_service.delete_children(
                        document_id=document_id,
                        block_id=root_block["block_id"],
                        start_index=start_index + inserted_count,
                        end_index=end_index + inserted_count,
                    )
                    del counts[start_block:end_block]
                    del new_states[start_block:end_block]
                if insert_items:
                    counts[start_block:start_block] = [
                        item.block_count for item in insert_items
                    ]
                    new_states[start_block:start_block] = insert_items
                offset_blocks += (j2 - j1) - (i2 - i1)

        for idx, item in enumerate(new_states):
            item.block_index = idx
        await self._block_service.replace_blocks(str(file_path), document_id, new_states)
        return True

    async def _rebuild_block_state(
        self,
        *,
        task: SyncTaskItem,
        docx_service: DocxService,
        document_id: str,
        markdown: str,
        base_path: str,
        file_path: Path,
        user_id_type: str,
    ) -> None:
        blocks = split_markdown_blocks(markdown)
        if not blocks:
            return
        now = time.time()
        file_hash = calculate_file_hash(file_path)
        items: list[BlockStateItem] = []
        for idx, block in enumerate(blocks):
            convert = await docx_service.convert_markdown_with_images(
                block,
                document_id=document_id,
                user_id_type=user_id_type,
                base_path=base_path,
            )
            convert = docx_service._normalize_convert(convert)
            items.append(
                BlockStateItem(
                    file_hash=file_hash,
                    local_path=str(file_path),
                    cloud_token=document_id,
                    block_index=idx,
                    block_hash=hash_block(block),
                    block_count=len(convert.first_level_block_ids),
                    updated_at=now,
                    created_at=now,
                )
            )
        await self._block_service.replace_blocks(str(file_path), document_id, items)

    async def _prefill_links_from_cloud(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> None:
        tree = await drive_service.scan_folder(
            task.cloud_folder_token, name=task.name or "同步根目录"
        )
        files = list(_flatten_files(tree))
        for node, relative_dir in files:
            token, node_type = _resolve_target(node)
            if node_type not in {"docx", "doc", "file", *(_EXPORT_EXTENSION_MAP.keys())}:
                continue
            target_dir = Path(task.local_path) / relative_dir
            if node_type in {"docx", "doc"}:
                local_path = target_dir / _docx_filename(node.name)
            elif node_type in _EXPORT_EXTENSION_MAP:
                local_path = target_dir / _export_filename(
                    node.name, _EXPORT_EXTENSION_MAP[node_type]
                )
            else:
                local_path = target_dir / sanitize_filename(node.name)
            await self._link_service.upsert_link(
                local_path=str(local_path),
                cloud_token=token,
                cloud_type=node_type,
                task_id=task.id,
                updated_at=0.0,
                cloud_parent_token=node.parent_token,
            )

def _flatten_files(node: DriveNode, base: Path | None = None) -> Iterable[tuple[DriveNode, Path]]:
    base = base or Path()
    for child in node.children:
        if child.type == "folder":
            if child.name == _CLOUD_MD_MIRROR_FOLDER_NAME:
                continue
            safe_name = sanitize_path_segment(child.name)
            yield from _flatten_files(child, base / safe_name)
        else:
            yield child, base


def _docx_filename(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".md"):
        return sanitize_filename(name)
    if lower.endswith(".docx") or lower.endswith(".doc"):
        return f"{sanitize_path_segment(Path(name).stem)}.md"
    return f"{sanitize_filename(name)}.md"


_EXPORT_EXTENSION_MAP = {
    "sheet": "xlsx",
    "bitable": "xlsx",
}


def _export_filename(name: str, extension: str) -> str:
    ext = extension.strip().lstrip(".")
    base = Path(name).stem if Path(name).suffix else name
    if not ext:
        return sanitize_filename(base)
    return sanitize_filename(f"{base}.{ext}")


def _extract_export_sub_id(url: str | None, file_type: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if not parsed.query:
        return None
    params = parse_qs(parsed.query)
    if file_type == "bitable":
        return _first_query_value(params, ("table", "table_id"))
    if file_type == "sheet":
        return _first_query_value(params, ("sheet", "sheet_id"))
    return None


def _first_query_value(params: dict[str, list[str]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        values = params.get(key)
        if not values:
            continue
        value = values[0].strip()
        if value:
            return value
    return None


def _parse_mtime(value: str | int | float | None) -> float:
    if value is None:
        return time.time()
    if isinstance(value, (int, float)):
        ts = float(value)
    else:
        raw = str(value).strip()
        try:
            ts = float(raw)
        except ValueError:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                ts = dt.timestamp()
            except ValueError:
                return time.time()
    if ts > 1e12:
        ts = ts / 1000.0
    return ts


def _contains_legacy_docx_placeholder(local_path: Path) -> bool:
    try:
        with local_path.open("r", encoding="utf-8", errors="ignore") as fp:
            snippet = fp.read(_LEGACY_DOCX_SCAN_BYTES)
    except OSError:
        return False
    return any(marker in snippet for marker in _LEGACY_DOCX_PLACEHOLDER_MARKERS)


def _resolve_target(node: DriveNode) -> tuple[str, str]:
    token = node.token
    node_type = node.type
    shortcut = node.shortcut_info
    if shortcut:
        token = shortcut.target_token or token
        node_type = shortcut.target_type or node_type
    return token, node_type


def _build_link_map(
    files: Iterable[tuple[DriveNode, Path]], local_root: str | Path
) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    root = Path(local_root)
    for node, relative_dir in files:
        token, node_type = _resolve_target(node)
        target_dir = root / relative_dir
        if node_type in {"docx", "doc"}:
            mapping[token] = target_dir / _docx_filename(node.name)
        elif node_type in _EXPORT_EXTENSION_MAP:
            mapping[token] = target_dir / _export_filename(
                node.name, _EXPORT_EXTENSION_MAP[node_type]
            )
        elif node_type == "file":
            mapping[token] = target_dir / sanitize_filename(node.name)
    return mapping


def _merge_synced_link_map(
    mapping: dict[str, Path], synced_links: Iterable[SyncLinkItem]
) -> dict[str, Path]:
    merged = dict(mapping)
    for item in synced_links:
        token = (item.cloud_token or "").strip()
        if not token or token in merged:
            continue
        local_path = Path(item.local_path)
        if local_path.exists() and local_path.is_file():
            merged[token] = local_path
    return merged


__all__ = ["SyncTaskRunner", "SyncTaskStatus", "SyncFileEvent"]
