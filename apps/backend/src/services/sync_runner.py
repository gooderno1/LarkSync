from __future__ import annotations

import asyncio
import difflib
import hashlib
import os
import re
import time
import uuid
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal
from urllib.parse import parse_qs, unquote, urlparse

from loguru import logger

from src.core.config import ConfigManager, DeletePolicy
from src.services.bitable_service import BitableService
from src.services.docx_service import (
    DocxService,
    has_markdown_table_exceeding_create_limit,
)
from src.services.drive_service import DriveFile, DriveNode, DriveService
from src.services.sheet_service import SheetService
from src.services.file_downloader import FileDownloader
from src.services.file_hash import calculate_file_hash
from src.services.file_uploader import FileUploader
from src.services.file_writer import FileWriter
from src.services.feishu_client import activate_cloud_root_scope, reset_cloud_root_scope
from src.services.markdown_blocks import hash_block, split_markdown_blocks
from src.services.path_sanitizer import sanitize_filename, sanitize_path_segment
from src.services.import_task_service import ImportTaskService
from src.services.export_task_service import ExportTaskError, ExportTaskResult, ExportTaskService
from src.services.conflict_service import ConflictService
from src.services.sync_block_service import BlockStateItem, SyncBlockService
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_event_pipeline import SyncEventPipeline
from src.services.sync_delete_sync_service import SyncDeleteSyncService
from src.services.sync_download_support_service import (
    DownloadCandidate,
    SyncDownloadSupportService,
)
from src.services.sync_download_orchestration_service import (
    DownloadRuntimeServices,
    SyncDownloadOrchestrationService,
)
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_path_upload_service import SyncPathUploadService
from src.services.sync_cloud_folder_service import SyncCloudFolderService
from src.services.sync_markdown_cloud_doc_service import SyncMarkdownCloudDocService
from src.services.sync_markdown_upload_service import SyncMarkdownUploadService
from src.services.sync_run_event_service import SyncRunEventService
from src.services.sync_run_service import SyncRunService
from src.services.sync_task_check_state_service import SyncTaskCheckStateService
from src.services.sync_runner_state import SYNC_LOG_LIMIT, SyncFileEvent, SyncState, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem
from src.services.sync_tombstone_service import SyncTombstoneService
from src.services.sync_upload_orchestration_service import (
    SyncUploadOrchestrationService,
    UploadRuntimeServices,
)
from src.services.transcoder import DocxTranscoder
from src.services.watcher import FileChangeEvent, WatcherService

_LOCAL_IMAGE_UPLOAD_REVISION_MARKER = "#local-images-v2"
_MARKDOWN_TABLE_RENDER_REVISION_MARKER = "#md-table-render-v10"
_MARKDOWN_IMAGE_REF_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
_MARKDOWN_LINK_REF_PATTERN = re.compile(r"(?<!!)\[[^\]]*]\(([^)]+)\)")
_HTML_IMAGE_REF_PATTERN = re.compile(
    r"""<img\b[^>]*\bsrc\s*=\s*(?P<quote>["'])(?P<src>.*?)(?P=quote)[^>]*>""",
    re.IGNORECASE | re.DOTALL,
)
_LEGACY_DOCX_PLACEHOLDER_MARKERS = (
    "sheet_token:",
    "内嵌表格（sheet_token:",
)
_LEGACY_DOCX_SCAN_BYTES = 262_144
_CLOUD_MD_MIRROR_FOLDER_NAME = "_LarkSync_MD_Mirror"
_CLOUD_MD_MIRROR_CACHE_PREFIX = "__md_mirror__"
_LOCAL_TRASH_DIR_NAME = ".larksync_trash"
_LOCAL_TEMP_FILE_PREFIXES = ("~$",)
_LOCAL_TEMP_FILE_SUFFIXES = (
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".part",
    ".crdownload",
    ".download",
)
_LOCAL_TEMP_FILE_NAMES = {
    ".ds_store",
    "desktop.ini",
    "thumbs.db",
}
_MD_SYNC_MODE_ENHANCED = "enhanced"
_MD_SYNC_MODE_DOWNLOAD_ONLY = "download_only"
_MD_SYNC_MODE_DOC_ONLY = "doc_only"
_MD_SYNC_MODE_VALUES = {
    _MD_SYNC_MODE_ENHANCED,
    _MD_SYNC_MODE_DOWNLOAD_ONLY,
    _MD_SYNC_MODE_DOC_ONLY,
}
_STARTUP_ADD_ONLY_THRESHOLD_SECONDS = 48 * 3600
_CHECK_ONLY_EVENT_STATUSES = {
    "queued",
    "reconcile_finished",
    "reconcile_started",
    "skipped",
    "started",
    "success",
}


def _is_temporary_local_name(name: str) -> bool:
    lowered = (name or "").strip().lower()
    if not lowered:
        return False
    if lowered in _LOCAL_TEMP_FILE_NAMES:
        return True
    if lowered.startswith(_LOCAL_TEMP_FILE_PREFIXES):
        return True
    if lowered.startswith(".~lock.") and lowered.endswith("#"):
        return True
    if lowered.endswith(_LOCAL_TEMP_FILE_SUFFIXES):
        return True
    return False


def _is_hidden_or_cache_relative_path(relative: Path) -> bool:
    for part in relative.parts:
        cleaned = part.strip()
        if not cleaned or cleaned == ".":
            continue
        lowered = cleaned.lower()
        if cleaned.startswith(".") or lowered == "__pycache__":
            return True
    return False


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
        run_event_service: SyncRunEventService | None = None,
        run_service: SyncRunService | None = None,
        check_state_service: SyncTaskCheckStateService | None = None,
        task_service: object | None = None,
        conflict_service: ConflictService | None = None,
        config_manager: ConfigManager | None = None,
        import_poll_attempts: int = 60,
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
        self._run_event_service = run_event_service or SyncRunEventService()
        self._run_service = run_service or SyncRunService()
        self._check_state_service = check_state_service
        self._task_service = task_service
        self._conflict_service = conflict_service or ConflictService()
        self._config_manager = config_manager or ConfigManager.get()
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
        self._pending_uploads: dict[str, dict[str, float]] = {}
        self._upload_quiet_window_seconds = 2.0
        self._running_tasks: set[str] = set()
        self._run_summary_write_lock = asyncio.Lock()
        self._task_meta: dict[str, SyncTaskItem] = {}
        self._pending_restarts: dict[str, SyncTaskItem] = {}
        self._initial_upload_scanned: set[str] = set()
        self._cloud_folder_service = SyncCloudFolderService(
            link_service=self._link_service,
            should_ignore_path=self._should_ignore_path,
            md_mirror_folder_name=_CLOUD_MD_MIRROR_FOLDER_NAME,
            md_mirror_cache_prefix=_CLOUD_MD_MIRROR_CACHE_PREFIX,
        )
        self._delete_sync_service = SyncDeleteSyncService(
            link_service=self._link_service,
            tombstone_service=self._tombstone_service,
            block_service=self._block_service,
            should_ignore_path=self._should_ignore_path,
            local_trash_dir_name=_LOCAL_TRASH_DIR_NAME,
        )
        self._markdown_cloud_doc_service = SyncMarkdownCloudDocService(
            link_service=self._link_service,
            block_service=self._block_service,
            resolve_cloud_parent=self._resolve_cloud_parent,
            find_existing_doc_by_name=self._find_existing_doc_by_name,
            wait_for_imported_doc=self._wait_for_imported_doc,
            list_folder_tokens=self._list_folder_tokens,
            list_files_all=self._list_files_all,
            get_local_signature=self._get_local_signature,
            calculate_local_resource_signature=self._calculate_local_resource_signature,
            build_cloud_revision=self._build_cloud_revision,
            parse_mtime=_parse_mtime,
            release_doc_lock=lambda token: self._doc_locks.pop(token, None),
        )
        self._download_support_service = SyncDownloadSupportService(
            export_extension_map=_EXPORT_EXTENSION_MAP,
            parse_mtime=_parse_mtime,
            contains_legacy_docx_placeholder=_contains_legacy_docx_placeholder,
            resolve_target=_resolve_target,
            docx_filename=_docx_filename,
            export_filename=_export_filename,
            generic_filename=sanitize_filename,
            extract_export_sub_id=_extract_export_sub_id,
            get_local_signature=self._get_local_signature,
        )
        self._event_pipeline = SyncEventPipeline(
            event_store=self._event_store,
            run_event_service=self._run_event_service,
            task_resolver=lambda task_id: self._task_meta.get(task_id),
            flush_delay_seconds=0.25,
            batch_size=100,
        )
        self._download_orchestration_service = SyncDownloadOrchestrationService(
            export_extension_map=_EXPORT_EXTENSION_MAP,
            flatten_folders=_flatten_folders,
            flatten_files=_flatten_files,
            build_link_map=_build_link_map,
            merge_synced_link_map=_merge_synced_link_map,
            folder_cloud_tokens=_folder_cloud_tokens,
            sync_cloud_folder_links=lambda *args, **kwargs: self._sync_cloud_folder_links(*args, **kwargs),
            build_download_candidate=lambda *args, **kwargs: self._build_download_candidate(*args, **kwargs),
            hydrate_export_sub_ids=lambda *args, **kwargs: self._hydrate_export_sub_ids(*args, **kwargs),
            should_ignore_path=lambda *args, **kwargs: self._should_ignore_path(*args, **kwargs),
            select_download_candidates=lambda *args, **kwargs: self._select_download_candidates(*args, **kwargs),
            matches_download_selection=lambda *args, **kwargs: self._matches_download_selection(*args, **kwargs),
            build_cloud_folder_paths=lambda *args, **kwargs: self._build_cloud_folder_paths(*args, **kwargs),
            enqueue_cloud_missing_deletes=lambda *args, **kwargs: self._enqueue_cloud_missing_deletes(*args, **kwargs),
            record_event=lambda *args, **kwargs: self._record_event(*args, **kwargs),
            should_skip_download_for_local_newer=lambda *args, **kwargs: self._should_skip_download_for_local_newer(*args, **kwargs),
            should_skip_download_for_unchanged=lambda *args, **kwargs: self._should_skip_download_for_unchanged(*args, **kwargs),
            download_docx=lambda *args, **kwargs: self._download_docx(*args, **kwargs),
            download_exported_file=lambda *args, **kwargs: self._download_exported_file(*args, **kwargs),
            get_local_signature=self._get_local_signature,
            build_cloud_revision=self._build_cloud_revision,
            calculate_local_resource_signature=self._calculate_local_resource_signature,
            rebuild_block_state=lambda *args, **kwargs: self._rebuild_block_state(*args, **kwargs),
            should_sync_md_cloud_mirror=lambda *args, **kwargs: self._should_sync_md_cloud_mirror(*args, **kwargs),
            sync_markdown_mirror_copy=lambda *args, **kwargs: self._sync_markdown_mirror_copy(*args, **kwargs),
            silence_path=self._silence_path,
            process_pending_deletes=lambda *args, **kwargs: self._process_pending_deletes(*args, **kwargs),
            write_markdown=self._file_writer.write_markdown,
        )
        self._upload_orchestration_service = SyncUploadOrchestrationService(
            prefill_links_from_cloud=lambda *args, **kwargs: self._prefill_links_from_cloud(*args, **kwargs),
            enqueue_missing_local_deletes=lambda *args, **kwargs: self._enqueue_missing_local_deletes(*args, **kwargs),
            iter_local_files=lambda *args, **kwargs: self._iter_local_files(*args, **kwargs),
            upload_path=lambda *args, **kwargs: self._upload_path(*args, **kwargs),
            process_pending_deletes=lambda *args, **kwargs: self._process_pending_deletes(*args, **kwargs),
            record_event=lambda *args, **kwargs: self._record_event(*args, **kwargs),
        )
        self._path_upload_service = SyncPathUploadService(
            uploading_paths=self._uploading_paths,
            link_service=self._link_service,
            should_ignore_path=lambda *args, **kwargs: self._should_ignore_path(*args, **kwargs),
            should_upload_markdown_doc=lambda *args, **kwargs: self._should_upload_markdown_doc(*args, **kwargs),
            upload_markdown=lambda *args, **kwargs: self._upload_markdown(*args, **kwargs),
            upload_file_callback=lambda *args, **kwargs: self._upload_file(*args, **kwargs),
            resolve_cloud_parent=lambda *args, **kwargs: self._resolve_cloud_parent(*args, **kwargs),
            get_local_signature=self._get_local_signature,
            build_cloud_revision=self._build_cloud_revision,
            list_files_all=lambda *args, **kwargs: self._list_files_all(*args, **kwargs),
            record_event=lambda *args, **kwargs: self._record_event(*args, **kwargs),
        )
        self._markdown_upload_service = SyncMarkdownUploadService(
            link_service=self._link_service,
            doc_locks=self._doc_locks,
            upload_file=lambda *args, **kwargs: self._upload_file(*args, **kwargs),
            create_cloud_doc_for_markdown=lambda *args, **kwargs: self._create_cloud_doc_for_markdown(*args, **kwargs),
            block_markdown_upload_when_cloud_changed=lambda *args, **kwargs: self._block_markdown_upload_when_cloud_changed(*args, **kwargs),
            list_block_states=lambda *args, **kwargs: self._block_service.list_blocks(*args, **kwargs),
            has_uploadable_markdown_images=self._has_uploadable_markdown_images,
            calculate_local_resource_signature=self._calculate_local_resource_signature,
            is_local_resource_state_synced=self._is_local_resource_state_synced,
            is_markdown_table_render_state_synced=self._is_markdown_table_render_state_synced,
            should_reimport_markdown_doc=self._should_reimport_markdown_doc,
            bootstrap_block_state=lambda *args, **kwargs: self._bootstrap_block_state(*args, **kwargs),
            apply_block_update=lambda *args, **kwargs: self._apply_block_update(*args, **kwargs),
            rebuild_block_state=lambda *args, **kwargs: self._rebuild_block_state(*args, **kwargs),
            reimport_cloud_doc_for_markdown=lambda *args, **kwargs: self._reimport_cloud_doc_for_markdown(*args, **kwargs),
            build_cloud_revision=self._build_cloud_revision,
            resolve_cloud_parent=lambda *args, **kwargs: self._resolve_cloud_parent(*args, **kwargs),
            should_sync_md_cloud_mirror=lambda *args, **kwargs: self._should_sync_md_cloud_mirror(*args, **kwargs),
            sync_markdown_mirror_copy=lambda *args, **kwargs: self._sync_markdown_mirror_copy(*args, **kwargs),
            cleanup_md_mirror_copy=lambda *args, **kwargs: self._cleanup_md_mirror_copy(*args, **kwargs),
            has_local_image_revision=_has_local_image_upload_revision,
            has_markdown_table_render_revision=_has_markdown_table_render_revision,
            record_event=lambda *args, **kwargs: self._record_event(*args, **kwargs),
        )

    @property
    def _cloud_folder_cache(self) -> dict[tuple[str, str], str]:
        return self._cloud_folder_service.cache

    @_cloud_folder_cache.setter
    def _cloud_folder_cache(self, value: dict[tuple[str, str], str]) -> None:
        self._cloud_folder_service.replace_cache(value)

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
        if (
            status.trigger_source == "scheduled_download"
            and status.current_run_id is None
        ):
            if event.status.strip().lower() in _CHECK_ONLY_EVENT_STATUSES:
                status.record_event(event)
                return
            self._activate_scheduled_activity_run(status, task)
        self._event_pipeline.record_event(status, event, task)

    def _activate_scheduled_activity_run(
        self,
        status: SyncTaskStatus,
        task: SyncTaskItem | None,
    ) -> None:
        if status.current_run_id is not None:
            return
        task_info = task or self._task_meta.get(status.task_id)
        if task_info is None or status.started_at is None:
            return
        status.current_run_id = str(uuid.uuid4())
        self._event_pipeline.record_event(
            status,
            SyncFileEvent(
                path=task_info.local_path,
                status="started",
                message="定时检查发现变化，开始执行同步",
                timestamp=status.started_at,
            ),
            task_info,
        )
        self._schedule_run_started(task_info, status)

    async def _flush_pending_events_now(self) -> None:
        await self._event_pipeline.flush_now()

    def ensure_watcher(self, task: SyncTaskItem) -> None:
        self._ensure_watcher(task)

    def stop_watcher(self, task_id: str) -> None:
        self._stop_watcher(task_id)

    async def close(self) -> None:
        for task in self._tasks.values():
            if task and not task.done():
                task.cancel()
        for task in self._tasks.values():
            if task and not task.done():
                with suppress(asyncio.CancelledError):
                    await task
        self._tasks.clear()
        self._running_tasks.clear()
        self._pending_restarts.clear()
        self._pending_uploads.clear()
        for task_id in list(self._watchers.keys()):
            self._stop_watcher(task_id)
        await self._event_pipeline.close()
        self._loop = None

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
            trigger_source="manual",
        )
        self._schedule_run_started(task, status)
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
        cloud_scope = activate_cloud_root_scope(task.cloud_folder_token)
        try:
            self._tasks[task.id] = asyncio.create_task(self.run_task(task))
        finally:
            reset_cloud_root_scope(cloud_scope)
        return status

    def cancel_task(self, task_id: str, *, preserve_pending_restart: bool = False) -> None:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
        status = self._statuses.get(task_id)
        if status and status.state == "running":
            status.state = "cancelled"
            status.last_error = "任务已取消"
            status.finished_at = time.time()
        self._running_tasks.discard(task_id)
        if not preserve_pending_restart:
            self._pending_uploads.pop(task_id, None)
            self._pending_restarts.pop(task_id, None)
        self._stop_watcher(task_id)

    def restart_task(self, task: SyncTaskItem, *, reason: str | None = None) -> SyncTaskStatus:
        self._task_meta[task.id] = task
        current = self._statuses.get(task.id)
        running = task.id in self._running_tasks
        active = self._tasks.get(task.id)
        if not running and (active is None or active.done()):
            return self.start_task(task)
        status = current or self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._pending_restarts[task.id] = task
        logger.info(
            "任务配置变更，准备重启: id={} reason={}",
            task.id,
            reason or "配置已更新",
        )
        self.cancel_task(task.id, preserve_pending_restart=True)
        return status

    def queue_local_change(
        self, task_id: str, path: Path, changed_at: float | None = None
    ) -> None:
        pending = self._pending_uploads.setdefault(task_id, {})
        pending[str(path)] = time.time() if changed_at is None else changed_at

    async def run_conflict_upload(
        self,
        task: SyncTaskItem,
        path: Path,
    ) -> SyncTaskStatus:
        return await self._run_manual_resolution(
            task,
            message=f"冲突处理：使用本地版本 {path.name}",
            executor=lambda status: self._run_upload_paths(
                task,
                status,
                [path],
                allow_deletes=False,
                force_paths={str(path)},
            ),
        )

    async def run_conflict_download(
        self,
        task: SyncTaskItem,
        path: Path,
        cloud_token: str,
    ) -> SyncTaskStatus:
        return await self._run_manual_resolution(
            task,
            message=f"冲突处理：使用云端版本 {path.name}",
            executor=lambda status: self._run_download(
                task,
                status,
                allow_deletes=False,
                selected_paths={str(path)},
                selected_cloud_tokens={cloud_token},
                force_paths={str(path)},
            ),
        )

    async def _run_manual_resolution(
        self,
        task: SyncTaskItem,
        *,
        message: str,
        executor,
    ) -> SyncTaskStatus:
        if task.id in self._running_tasks:
            raise RuntimeError("任务运行中，请稍后再试")
        self._running_tasks.add(task.id)
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(
            task,
            status,
            message=message,
            trigger_source="conflict_resolution",
        )
        await self._persist_run_started(task, status)
        cloud_scope = activate_cloud_root_scope(task.cloud_folder_token)
        try:
            await executor(status)
            status.state = "failed" if status.failed_files > 0 else "success"
            status.finished_at = time.time()
            return status
        except Exception as exc:
            status.state = "failed"
            status.last_error = str(exc)
            status.finished_at = time.time()
            raise
        finally:
            if status.state == "running":
                status.state = "failed" if status.failed_files > 0 else "success"
                status.finished_at = time.time()
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
            await self._finalize_run_status(task, status)
            self._running_tasks.discard(task.id)
            reset_cloud_root_scope(cloud_scope)

    async def run_scheduled_upload(self, task: SyncTaskItem) -> None:
        # 双向任务启动时通常会先执行下行；此时不要再并发扫描同一目录。
        if task.id in self._running_tasks:
            return
        # 首次调度时，全量扫描本地目录，将没有 SyncLink 的文件加入待上传队列
        if task.id not in self._initial_upload_scanned:
            self._initial_upload_scanned.add(task.id)
            await self._scan_for_unlinked_files(task)

        pending = self._pending_uploads.get(task.id) or {}
        has_pending_tombstone = await self._has_pending_tombstones(task.id)
        # 扫描和查询期间可能已有下行任务开始，避免同一任务双向并发。
        if task.id in self._running_tasks:
            return
        ready_paths: list[Path] = []
        if pending:
            now = time.time()
            ready_keys = [
                path
                for path, changed_at in pending.items()
                if (now - changed_at) >= self._upload_quiet_window_seconds
            ]
            ready_paths = [Path(path) for path in sorted(ready_keys)]
            for path in ready_keys:
                pending.pop(path, None)
        if not ready_paths and not has_pending_tombstone:
            if self._check_state_service is not None:
                now = time.time()
                await self._check_state_service.mark_finished(
                    task_id=task.id,
                    trigger_source="scheduled_upload",
                    started_at=now,
                    finished_at=now,
                    change_count=0,
                )
            return
        self._running_tasks.add(task.id)
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(
            task,
            status,
            message="周期上传触发",
            trigger_source="scheduled_upload",
        )
        await self._persist_run_started(task, status)
        if self._check_state_service is not None and status.started_at is not None:
            await self._check_state_service.mark_started(
                task_id=task.id,
                trigger_source="scheduled_upload",
                started_at=status.started_at,
            )
        cloud_scope = activate_cloud_root_scope(task.cloud_folder_token)
        try:
            await self._run_additive_reconciliation_if_needed(task, status)
            await self._run_upload_paths(task, status, ready_paths)
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
            await self._finalize_run_status(task, status)
            self._running_tasks.discard(task.id)
            reset_cloud_root_scope(cloud_scope)

    async def run_scheduled_download(self, task: SyncTaskItem) -> None:
        if task.id in self._running_tasks:
            return
        self._running_tasks.add(task.id)
        self._task_meta[task.id] = task
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        self._reset_status(
            task,
            status,
            message="定时下载触发",
            trigger_source="scheduled_download",
            defer_run_until_activity=True,
        )
        if self._check_state_service is not None and status.started_at is not None:
            await self._check_state_service.mark_started(
                task_id=task.id,
                trigger_source="scheduled_download",
                started_at=status.started_at,
            )
        cloud_scope = activate_cloud_root_scope(task.cloud_folder_token)
        try:
            await self._run_additive_reconciliation_if_needed(task, status)
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
            await self._finalize_run_status(task, status)
            self._running_tasks.discard(task.id)
            reset_cloud_root_scope(cloud_scope)

    def _reset_status(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        message: str,
        *,
        trigger_source: str,
        defer_run_until_activity: bool = False,
    ) -> None:
        status.state = "running"
        status.trigger_source = trigger_source
        status.started_at = time.time()
        status.finished_at = None
        status.current_run_id = None if defer_run_until_activity else str(uuid.uuid4())
        status.total_files = 0
        status.completed_files = 0
        status.failed_files = 0
        status.skipped_files = 0
        status.uploaded_files = 0
        status.downloaded_files = 0
        status.deleted_files = 0
        status.conflict_files = 0
        status.delete_pending_files = 0
        status.delete_failed_files = 0
        status.last_error = None
        status.last_files = []
        if not defer_run_until_activity:
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
            await self._run_additive_reconciliation_if_needed(task, status)
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
            await self._finalize_run_status(task, status)
            self._tasks.pop(task.id, None)
            self._running_tasks.discard(task.id)
            pending_restart = self._pending_restarts.pop(task.id, None)
            if pending_restart and pending_restart.enabled:
                self.start_task(pending_restart)

    async def _run_additive_reconciliation_if_needed(
        self, task: SyncTaskItem, status: SyncTaskStatus
    ) -> None:
        if not self._task_service:
            return
        if not self._needs_additive_reconciliation(task):
            return
        last_run = task.last_run_at
        reason = "新建任务" if last_run is None else "距离上次运行超过 48 小时"
        self._record_event(
            status,
            SyncFileEvent(
                path=task.local_path,
                status="reconcile_started",
                message=f"{reason}，先执行无删除补齐",
            ),
            task,
        )
        logger.info(
            "启动无删除补齐: task_id={} mode={} last_run_at={}",
            task.id,
            task.sync_mode,
            last_run,
        )
        preexisting_local_files: list[Path] = []
        if task.sync_mode == "bidirectional":
            preexisting_local_files = list(self._iter_local_files(task))
        if task.sync_mode in {"bidirectional", "download_only"}:
            await self._run_download(task, status, allow_deletes=False)
        if task.sync_mode == "bidirectional":
            await self._run_upload_paths(
                task,
                status,
                preexisting_local_files,
                allow_deletes=False,
            )
        elif task.sync_mode == "upload_only":
            await self._run_upload(task, status, allow_deletes=False)
        self._record_event(
            status,
            SyncFileEvent(
                path=task.local_path,
                status="reconcile_finished",
                message="无删除补齐完成，继续执行本次常规同步",
            ),
            task,
        )

    @staticmethod
    def _needs_additive_reconciliation(task: SyncTaskItem) -> bool:
        last_run = task.last_run_at
        if last_run is None:
            return True
        try:
            return (time.time() - float(last_run)) > _STARTUP_ADD_ONLY_THRESHOLD_SECONDS
        except (TypeError, ValueError):
            return True

    def _schedule_run_started(self, task: SyncTaskItem, status: SyncTaskStatus) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._persist_run_started(task, status))

    async def _persist_run_started(
        self, task: SyncTaskItem, status: SyncTaskStatus
    ) -> None:
        if not status.current_run_id or status.started_at is None:
            return
        try:
            async with self._run_summary_write_lock:
                await self._run_service.start_run(
                    run_id=status.current_run_id,
                    task_id=task.id,
                    trigger_source=status.trigger_source or "manual",
                    started_at=status.started_at,
                )
        except Exception:
            logger.exception(
                "创建运行摘要失败: task_id={} run_id={}",
                task.id,
                status.current_run_id,
            )

    async def _persist_run_finished(
        self, task: SyncTaskItem, status: SyncTaskStatus
    ) -> None:
        if not status.current_run_id:
            return
        last_event_at = status.finished_at
        if status.last_files:
            last_event_at = status.last_files[-1].timestamp
        try:
            async with self._run_summary_write_lock:
                await self._run_service.finish_run(
                    run_id=status.current_run_id,
                    task_id=task.id,
                    trigger_source=status.trigger_source or "manual",
                    state=status.state,
                    started_at=status.started_at,
                    finished_at=status.finished_at,
                    last_event_at=last_event_at,
                    total_files=status.total_files,
                    completed_files=status.completed_files,
                    failed_files=status.failed_files,
                    skipped_files=status.skipped_files,
                    uploaded_files=status.uploaded_files,
                    downloaded_files=status.downloaded_files,
                    deleted_files=status.deleted_files,
                    conflict_files=status.conflict_files,
                    delete_pending_files=status.delete_pending_files,
                    delete_failed_files=status.delete_failed_files,
                    last_error=status.last_error,
                    run_kind="activity",
                    has_activity=True,
                )
        except Exception:
            logger.exception(
                "更新运行摘要失败: task_id={} run_id={}",
                task.id,
                status.current_run_id,
            )

    async def _finalize_run_status(
        self, task: SyncTaskItem, status: SyncTaskStatus
    ) -> None:
        await self._flush_pending_events_now()
        await self._persist_run_finished(task, status)
        if (
            self._check_state_service is not None
            and (status.trigger_source or "").startswith("scheduled_")
            and status.finished_at is not None
        ):
            change_count = (
                status.uploaded_files
                + status.downloaded_files
                + status.deleted_files
                + status.conflict_files
                + status.delete_pending_files
                + status.delete_failed_files
                + status.failed_files
            )
            await self._check_state_service.mark_finished(
                task_id=task.id,
                trigger_source=status.trigger_source or "scheduled_download",
                started_at=status.started_at,
                finished_at=status.finished_at,
                change_count=change_count,
                last_error=status.last_error,
            )
        if status.state != "cancelled":
            await self._mark_task_run(task)
        status.current_run_id = None

    async def _mark_task_run(self, task: SyncTaskItem) -> None:
        service = self._task_service
        if not service:
            return
        mark_task_run = getattr(service, "mark_task_run", None)
        if not callable(mark_task_run):
            return
        try:
            await mark_task_run(task.id, run_at=time.time())
        except Exception:
            logger.exception("更新任务运行时间失败: task_id={}", task.id)

    async def _run_download(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        *,
        allow_deletes: bool = True,
        selected_paths: set[str] | None = None,
        selected_cloud_tokens: set[str] | None = None,
        force_paths: set[str] | None = None,
    ) -> None:
        self._task_meta[task.id] = task
        runtime = self._resolve_download_runtime_services()
        await self._download_orchestration_service.run_download(
            task=task,
            status=status,
            runtime=runtime,
            allow_deletes=allow_deletes,
            selected_paths=selected_paths,
            selected_cloud_tokens=selected_cloud_tokens,
            force_paths=force_paths,
        )

    def _resolve_download_runtime_services(self) -> DownloadRuntimeServices:
        drive_service = self._drive_service or DriveService()
        docx_service = self._docx_service or DocxService()
        sheet_service = self._sheet_service or SheetService()
        transcoder = self._transcoder or DocxTranscoder(sheet_service=sheet_service)
        file_downloader = self._file_downloader or FileDownloader()
        file_uploader = self._file_uploader or FileUploader()
        export_task_service = self._export_task_service or ExportTaskService()
        bitable_service = self._bitable_service or BitableService()
        owned_services: list[object] = []
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
        return DownloadRuntimeServices(
            drive_service=drive_service,
            docx_service=docx_service,
            sheet_service=sheet_service,
            transcoder=transcoder,
            file_downloader=file_downloader,
            file_uploader=file_uploader,
            export_task_service=export_task_service,
            bitable_service=bitable_service,
            link_service=self._link_service,
            owned_services=owned_services,
        )

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
        service = SyncDownloadSupportService(
            export_extension_map=_EXPORT_EXTENSION_MAP,
            parse_mtime=_parse_mtime,
            contains_legacy_docx_placeholder=_contains_legacy_docx_placeholder,
            resolve_target=_resolve_target,
            docx_filename=_docx_filename,
            export_filename=_export_filename,
            generic_filename=sanitize_filename,
            extract_export_sub_id=_extract_export_sub_id,
            get_local_signature=SyncTaskRunner._get_local_signature,
        )
        return service.should_skip_download_for_unchanged(
            local_path=local_path,
            cloud_mtime=cloud_mtime,
            persisted=persisted,
            effective_token=effective_token,
            effective_type=effective_type,
        )

    @staticmethod
    def _build_download_candidate(
        task: SyncTaskItem,
        node: DriveNode,
        relative_dir: Path,
    ) -> DownloadCandidate:
        service = SyncDownloadSupportService(
            export_extension_map=_EXPORT_EXTENSION_MAP,
            parse_mtime=_parse_mtime,
            contains_legacy_docx_placeholder=_contains_legacy_docx_placeholder,
            resolve_target=_resolve_target,
            docx_filename=_docx_filename,
            export_filename=_export_filename,
            generic_filename=sanitize_filename,
            extract_export_sub_id=_extract_export_sub_id,
            get_local_signature=SyncTaskRunner._get_local_signature,
        )
        return service.build_download_candidate(task, node, relative_dir)

    async def _hydrate_export_sub_ids(
        self,
        candidates: list[DownloadCandidate],
        drive_service: DriveService,
        *,
        sheet_service: SheetService | None = None,
        bitable_service: BitableService | None = None,
    ) -> list[DownloadCandidate]:
        return await self._download_support_service.hydrate_export_sub_ids(
            candidates,
            drive_service,
            sheet_service=sheet_service,
            bitable_service=bitable_service,
        )

    @staticmethod
    def _select_download_candidates(
        candidates: list[DownloadCandidate],
        persisted_by_path: dict[str, SyncLinkItem],
    ) -> tuple[list[DownloadCandidate], list[DownloadCandidate]]:
        service = SyncDownloadSupportService(
            export_extension_map=_EXPORT_EXTENSION_MAP,
            parse_mtime=_parse_mtime,
            contains_legacy_docx_placeholder=_contains_legacy_docx_placeholder,
            resolve_target=_resolve_target,
            docx_filename=_docx_filename,
            export_filename=_export_filename,
            generic_filename=sanitize_filename,
            extract_export_sub_id=_extract_export_sub_id,
            get_local_signature=SyncTaskRunner._get_local_signature,
        )
        return service.select_download_candidates(candidates, persisted_by_path)

    @staticmethod
    def _choose_download_candidate(
        *,
        current: DownloadCandidate,
        candidate: DownloadCandidate,
        persisted: SyncLinkItem | None,
    ) -> DownloadCandidate:
        return SyncDownloadSupportService.choose_download_candidate(
            current=current,
            candidate=candidate,
            persisted=persisted,
        )

    async def _download_docx(
        self,
        document_id: str,
        *,
        docx_service: DocxService,
        transcoder: DocxTranscoder,
        base_dir: Path | None = None,
        link_map: dict[str, Path] | None = None,
    ) -> str:
        return await self._download_support_service.download_docx(
            document_id,
            docx_service=docx_service,
            transcoder=transcoder,
            base_dir=base_dir,
            link_map=link_map,
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
        await self._download_support_service.download_exported_file(
            export_task_service=export_task_service,
            file_downloader=file_downloader,
            file_token=file_token,
            file_type=file_type,
            target_path=target_path,
            mtime=mtime,
            export_extension=export_extension,
            export_sub_id=export_sub_id,
            poll_attempts=self._export_poll_attempts,
            poll_interval=self._export_poll_interval,
        )

    async def _wait_for_export_task(
        self,
        export_task_service: ExportTaskService,
        ticket: str,
        *,
        file_token: str | None = None,
    ) -> ExportTaskResult:
        return await self._download_support_service.wait_for_export_task(
            export_task_service,
            ticket,
            file_token=file_token,
            poll_attempts=self._export_poll_attempts,
            poll_interval=self._export_poll_interval,
        )

    async def _run_upload(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        *,
        allow_deletes: bool = True,
    ) -> None:
        self._task_meta[task.id] = task
        runtime = self._resolve_upload_runtime_services()
        await self._upload_orchestration_service.run_upload(
            task=task,
            status=status,
            runtime=runtime,
            allow_deletes=allow_deletes,
        )

    async def _run_upload_paths(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        paths: Iterable[Path],
        *,
        allow_deletes: bool = True,
        force_paths: set[str] | None = None,
    ) -> None:
        runtime = self._resolve_upload_runtime_services()
        await self._upload_orchestration_service.run_upload_paths(
            task=task,
            status=status,
            paths=paths,
            runtime=runtime,
            allow_deletes=allow_deletes,
            force_paths=force_paths,
        )

    def _resolve_upload_runtime_services(self) -> UploadRuntimeServices:
        docx_service = self._docx_service or DocxService()
        file_uploader = self._file_uploader or FileUploader()
        drive_service = self._drive_service or DriveService()
        import_task_service = self._import_task_service or ImportTaskService()
        owned_services: list[object] = []
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._file_uploader is None:
            owned_services.append(file_uploader)
        if self._drive_service is None:
            owned_services.append(drive_service)
        if self._import_task_service is None:
            owned_services.append(import_task_service)
        return UploadRuntimeServices(
            docx_service=docx_service,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            owned_services=owned_services,
        )

    async def _upload_path(
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
        await self._path_upload_service.upload_path(
            task,
            status,
            path,
            docx_service,
            file_uploader,
            drive_service,
            import_task_service,
            force=force,
        )

    async def _upload_markdown(
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
        await self._markdown_upload_service.upload_markdown(
            task,
            status,
            path,
            docx_service,
            file_uploader,
            drive_service,
            import_task_service,
            force=force,
        )

    async def _block_markdown_upload_when_cloud_changed(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        link: SyncLinkItem,
        file_hash: str,
        markdown: str,
        drive_service: DriveService,
        force: bool = False,
    ) -> bool:
        """双向同步上传前校验云端是否相对本地基线已变化。"""
        if force:
            logger.info(
                "冲突处理按本地优先强制覆盖云端: task_id={} path={} token={}",
                task.id,
                path,
                link.cloud_token,
            )
            return False
        if task.sync_mode != "bidirectional":
            return False
        if link.cloud_type not in {"docx", "doc"}:
            return False

        baseline_mtime = self._cloud_mtime_baseline(link)
        try:
            cloud_mtime = await self._fetch_linked_cloud_mtime(
                task=task,
                path=path,
                link=link,
                drive_service=drive_service,
            )
        except Exception as exc:
            status.failed_files += 1
            status.last_error = f"上传前云端状态校验失败: {exc}"
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="上传前无法确认云端是否更新，已阻止覆盖",
                ),
            )
            logger.warning(
                "上传前云端状态校验失败，阻止覆盖: task_id={} path={} token={} error={}",
                task.id,
                path,
                link.cloud_token,
                exc,
            )
            return True

        if cloud_mtime is None or cloud_mtime <= baseline_mtime + 1.0:
            return False

        db_hash = link.local_hash or ""
        if db_hash and db_hash == file_hash:
            status.skipped_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="skipped",
                    message="云端已更新，等待下载",
                ),
            )
            logger.info(
                "云端已更新且本地未变，跳过上传等待下载: task_id={} path={} token={} cloud_mtime={} baseline={}",
                task.id,
                path,
                link.cloud_token,
                cloud_mtime,
                baseline_mtime,
            )
            return True

        await self._conflict_service.add_conflict(
            local_path=str(path),
            cloud_token=link.cloud_token,
            local_hash=file_hash,
            db_hash=db_hash,
            cloud_version=self._mtime_to_version(cloud_mtime),
            db_version=self._mtime_to_version(baseline_mtime),
            local_preview=self._preview_markdown(markdown),
            cloud_preview=None,
        )
        status.skipped_files += 1
        self._record_event(
            status,
            SyncFileEvent(
                path=str(path),
                status="conflict",
                message="云端已更新，已阻止本地覆盖",
            ),
        )
        logger.warning(
            "检测到云端先于上传发生变化，已记录冲突并阻止覆盖: task_id={} path={} token={} cloud_mtime={} baseline={}",
            task.id,
            path,
            link.cloud_token,
            cloud_mtime,
            baseline_mtime,
        )
        return True

    async def _fetch_linked_cloud_mtime(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        link: SyncLinkItem,
        drive_service: DriveService,
    ) -> float | None:
        parent_token = link.cloud_parent_token
        if not parent_token:
            parent_token = await self._resolve_cloud_parent(task, path, drive_service)
        items = await self._list_files_all(drive_service, parent_token)
        for item in items:
            if item.token == link.cloud_token:
                if item.modified_time is None:
                    return None
                return _parse_mtime(item.modified_time)
        return None

    @staticmethod
    def _cloud_mtime_baseline(link: SyncLinkItem) -> float:
        if link.cloud_mtime is not None:
            return float(link.cloud_mtime)
        return float(link.updated_at or 0.0)

    @staticmethod
    def _mtime_to_version(mtime: float) -> int:
        return int(max(0.0, mtime) * 1000)

    @staticmethod
    def _preview_markdown(markdown: str, limit: int = 2000) -> str:
        return markdown[:limit]

    @staticmethod
    def _should_reimport_markdown_doc(
        markdown: str, *, has_uploadable_images: bool = False
    ) -> bool:
        return has_markdown_table_exceeding_create_limit(
            markdown
        ) and not has_uploadable_images

    @staticmethod
    def _has_uploadable_markdown_images(markdown: str, base_path: str | Path | None) -> bool:
        for match in _MARKDOWN_IMAGE_REF_PATTERN.finditer(markdown):
            ref = _normalize_markdown_resource_ref(match.group(1))
            if _is_uploadable_markdown_image_ref(ref, base_path):
                return True
        for match in _HTML_IMAGE_REF_PATTERN.finditer(markdown):
            ref = (match.group("src") or "").strip()
            if _is_uploadable_markdown_image_ref(ref, base_path):
                return True
        return False

    @staticmethod
    def _calculate_local_resource_signature(
        markdown: str,
        base_path: str | Path | None,
    ) -> str | None:
        entries: list[str] = []
        for match in _MARKDOWN_IMAGE_REF_PATTERN.finditer(markdown):
            ref = _normalize_markdown_resource_ref(match.group(1))
            entry = _build_local_resource_signature_entry(ref, base_path, image_only=True)
            if entry:
                entries.append(entry)
        for match in _HTML_IMAGE_REF_PATTERN.finditer(markdown):
            ref = (match.group("src") or "").strip()
            entry = _build_local_resource_signature_entry(ref, base_path, image_only=True)
            if entry:
                entries.append(entry)
        for match in _MARKDOWN_LINK_REF_PATTERN.finditer(markdown):
            ref = _normalize_markdown_resource_ref(match.group(1))
            entry = _build_local_resource_signature_entry(ref, base_path, image_only=False)
            if entry:
                entries.append(entry)
        if not entries:
            return None
        payload = "\n".join(sorted(set(entries)))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_local_resource_state_synced(
        *,
        link: SyncLinkItem,
        resource_signature: str | None,
        has_uploadable_images: bool,
        local_images_repaired: bool,
    ) -> bool:
        if resource_signature is None:
            return True
        if (
            link.local_resource_signature == resource_signature
            and link.resource_sync_revision
            and link.cloud_revision
            and link.resource_sync_revision == link.cloud_revision
        ):
            return True
        return (not has_uploadable_images) and local_images_repaired

    @staticmethod
    def _is_markdown_table_render_state_synced(
        *,
        repair_required: bool,
        repaired: bool,
    ) -> bool:
        return (not repair_required) or repaired

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
        if task.sync_mode == "download_only":
            return False
        return self._resolve_md_sync_mode(task) != _MD_SYNC_MODE_DOWNLOAD_ONLY

    def _should_sync_md_cloud_mirror(self, task: SyncTaskItem) -> bool:
        if task.sync_mode == "download_only":
            return False
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
        return SyncDeleteSyncService.normalize_delete_policy(raw_policy)

    def _resolve_delete_policy(self, task: SyncTaskItem | None = None) -> tuple[DeletePolicy, float]:
        return self._delete_sync_service.resolve_delete_policy(task)

    async def _has_pending_tombstones(self, task_id: str) -> bool:
        return await self._delete_sync_service.has_pending_tombstones(task_id)

    @staticmethod
    def _build_cloud_revision(
        cloud_token: str,
        cloud_mtime: float | None,
        *,
        local_images_uploaded: bool = False,
        markdown_tables_rendered: bool = False,
    ) -> str | None:
        token = (cloud_token or "").strip()
        if not token:
            return None
        suffix = ""
        if local_images_uploaded:
            suffix += _LOCAL_IMAGE_UPLOAD_REVISION_MARKER
        if markdown_tables_rendered:
            suffix += _MARKDOWN_TABLE_RENDER_REVISION_MARKER
        if cloud_mtime is None:
            return f"{token}{suffix}"
        return f"{token}@{int(cloud_mtime * 1000)}{suffix}"

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
        return await self._delete_sync_service.enqueue_local_delete_tombstone(
            task=task,
            status=status,
            local_path=local_path,
            reason=reason,
            record_event=self._record_event,
        )

    async def _enqueue_missing_local_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
    ) -> None:
        await self._delete_sync_service.enqueue_missing_local_deletes(
            task=task,
            status=status,
            record_event=self._record_event,
        )

    async def _enqueue_cloud_missing_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        persisted_links: list[SyncLinkItem],
        cloud_paths: set[str],
    ) -> None:
        await self._delete_sync_service.enqueue_cloud_missing_deletes(
            task=task,
            status=status,
            persisted_links=persisted_links,
            cloud_paths=cloud_paths,
            record_event=self._record_event,
        )

    async def _process_pending_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        drive_service: DriveService,
        known_cloud_tokens: set[str] | None = None,
    ) -> None:
        await self._delete_sync_service.process_pending_deletes(
            task=task,
            status=status,
            drive_service=drive_service,
            known_cloud_tokens=known_cloud_tokens,
            record_event=self._record_event,
            cleanup_md_mirror_copy=self._cleanup_md_mirror_copy,
            silence_path=self._silence_path,
        )

    async def _cleanup_deleted_state(
        self,
        *,
        task_id: str,
        local_path: str,
        cloud_token: str | None,
        recursive: bool = False,
    ) -> None:
        await self._delete_sync_service.cleanup_deleted_state(
            task_id=task_id,
            local_path=local_path,
            cloud_token=cloud_token,
            recursive=recursive,
        )

    async def _find_active_link_for_cloud_token(
        self,
        *,
        task: SyncTaskItem,
        cloud_token: str,
        excluding_local_path: str,
    ) -> SyncLinkItem | None:
        return await self._delete_sync_service.find_active_link_for_cloud_token(
            task=task,
            cloud_token=cloud_token,
            excluding_local_path=excluding_local_path,
        )

    @staticmethod
    def _normalize_local_path_key(path: str | Path) -> str:
        return SyncDeleteSyncService.normalize_local_path_key(path)

    @classmethod
    def _is_same_or_descendant_path(
        cls,
        path: str | Path,
        ancestor: str | Path,
    ) -> bool:
        return SyncDeleteSyncService.is_same_or_descendant_path(path, ancestor)

    def _move_to_local_trash(self, task: SyncTaskItem, local_path: Path) -> Path:
        return self._delete_sync_service.move_to_local_trash(
            task,
            local_path,
            silence_path=self._silence_path,
        )

    @staticmethod
    def _is_cloud_already_deleted_error(exc: Exception) -> bool:
        return SyncDeleteSyncService.is_cloud_already_deleted_error(exc)

    async def _cleanup_md_mirror_copy(
        self,
        *,
        task: SyncTaskItem,
        local_path: Path,
        drive_service: DriveService,
    ) -> None:
        await self._cloud_folder_service.cleanup_md_mirror_copy(
            task=task,
            local_path=local_path,
            drive_service=drive_service,
            supports_md_cloud_mirror=self._supports_md_cloud_mirror,
            is_cloud_already_deleted_error=self._is_cloud_already_deleted_error,
        )

    async def _find_md_mirror_parent_no_create(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str | None:
        return await self._cloud_folder_service.find_md_mirror_parent_no_create(
            task=task,
            path=path,
            drive_service=drive_service,
        )

    async def _find_md_mirror_root_no_create(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str | None:
        return await self._cloud_folder_service.find_md_mirror_root_no_create(
            task,
            drive_service,
        )

    async def _resolve_md_mirror_parent(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        return await self._cloud_folder_service.resolve_md_mirror_parent(
            task=task,
            path=path,
            drive_service=drive_service,
        )

    async def _ensure_md_mirror_root(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str:
        return await self._cloud_folder_service.ensure_md_mirror_root(
            task,
            drive_service,
        )

    async def _upload_file(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService | None = None,
        *,
        force: bool = False,
    ) -> None:
        await self._path_upload_service.upload_file(
            task,
            status,
            path,
            file_uploader,
            drive_service,
            force=force,
        )

    async def _cleanup_replaced_cloud_files(
        self,
        *,
        path: Path,
        new_token: str,
        parent_token: str,
        previous_link: SyncLinkItem | None,
        drive_service: DriveService | None,
    ) -> None:
        await self._path_upload_service.cleanup_replaced_cloud_files(
            path=path,
            new_token=new_token,
            parent_token=parent_token,
            previous_link=previous_link,
            drive_service=drive_service,
        )

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
        return await self._markdown_cloud_doc_service.create_cloud_doc_for_markdown(
            task=task,
            status=status,
            path=path,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            record_event=self._record_event,
        )

    async def _reimport_cloud_doc_for_markdown(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        old_link: SyncLinkItem,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> SyncLinkItem | None:
        return await self._markdown_cloud_doc_service.reimport_cloud_doc_for_markdown(
            task=task,
            status=status,
            path=path,
            old_link=old_link,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            record_event=self._record_event,
        )

    async def _import_markdown_doc(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        parent_token: str,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> DriveFile | None:
        return await self._markdown_cloud_doc_service.import_markdown_doc(
            task=task,
            status=status,
            path=path,
            parent_token=parent_token,
            file_uploader=file_uploader,
            drive_service=drive_service,
            import_task_service=import_task_service,
            record_event=self._record_event,
        )

    async def _cleanup_duplicate_docs_by_name(
        self,
        *,
        drive_service: DriveService,
        parent_token: str,
        expected_name: str,
        keep_token: str,
        path: Path,
    ) -> None:
        await self._markdown_cloud_doc_service.cleanup_duplicate_docs_by_name(
            drive_service=drive_service,
            parent_token=parent_token,
            expected_name=expected_name,
            keep_token=keep_token,
            path=path,
        )

    async def _cleanup_import_source_file(
        self,
        *,
        drive_service: DriveService,
        source_file_token: str | None,
        task_id: str,
        parent_token: str,
        source_name: str,
    ) -> None:
        await self._markdown_cloud_doc_service.cleanup_import_source_file(
            drive_service=drive_service,
            source_file_token=source_file_token,
            task_id=task_id,
            parent_token=parent_token,
            source_name=source_name,
        )

    def _iter_local_files(self, task: SyncTaskItem) -> Iterable[Path]:
        root = Path(task.local_path)
        if not root.exists():
            return []
        return [
            path
            for path in root.rglob("*")
            if path.is_file() and not self._should_ignore_path(task, path)
        ]

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
        links = await self._link_service.list_by_task(task.id)
        linked_paths = {
            os.path.normcase(os.path.normpath(link.local_path)) for link in links
        }

        def _collect_candidates() -> list[Path]:
            candidates: list[Path] = []
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if self._should_ignore_path(task, path):
                    continue
                if skip_md and path.suffix.lower() == ".md":
                    continue
                path_key = os.path.normcase(os.path.normpath(str(path)))
                if path_key not in linked_paths:
                    candidates.append(path)
            return candidates

        # 大目录遍历是阻塞 I/O，放到工作线程避免拖住 API 和桌面窗口渲染。
        candidates = await asyncio.to_thread(_collect_candidates)
        for path in candidates:
            self.queue_local_change(task.id, path, changed_at=0.0)
        queued = len(candidates)
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
        if _is_temporary_local_name(relative.name):
            return True
        lowered = {part.lower() for part in relative.parts}
        if (
            "assets" in lowered
            or "attachments" in lowered
            or "figures" in lowered
            or "插图" in relative.parts
            or _LOCAL_TRASH_DIR_NAME.lower() in lowered
            or _CLOUD_MD_MIRROR_FOLDER_NAME.lower() in lowered
        ):
            return True
        if (
            ConfigManager.get().config.ignore_hidden_cache_paths
            and _is_hidden_or_cache_relative_path(relative)
        ):
            return True
        relative_parts = tuple(part.lower() for part in relative.parts if part and part != ".")
        for ignored in task.ignored_subpaths:
            ignored_parts = tuple(
                part.lower()
                for part in Path(ignored.replace("\\", "/")).parts
                if part and part != "."
            )
            if ignored_parts and relative_parts[: len(ignored_parts)] == ignored_parts:
                return True
        return False

    @staticmethod
    def _matches_download_selection(
        candidate: DownloadCandidate,
        *,
        selected_paths: set[str] | None,
        selected_cloud_tokens: set[str] | None,
    ) -> bool:
        path_selected = (
            True if not selected_paths else str(candidate.target_path) in selected_paths
        )
        token_selected = (
            True
            if not selected_cloud_tokens
            else candidate.effective_token in selected_cloud_tokens
        )
        return path_selected and token_selected

    async def _resolve_cloud_parent(
        self,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        return await self._cloud_folder_service.resolve_cloud_parent(
            task,
            path,
            drive_service,
        )

    async def _link_local_folder(
        self,
        *,
        task: SyncTaskItem,
        relative_folder: Path,
        cloud_token: str,
        cloud_parent_token: str | None,
    ) -> None:
        await self._cloud_folder_service.link_local_folder(
            task=task,
            relative_folder=relative_folder,
            cloud_token=cloud_token,
            cloud_parent_token=cloud_parent_token,
        )

    async def _find_subfolder(
        self,
        drive_service: DriveService,
        parent_token: str,
        name: str,
    ) -> str | None:
        return await self._cloud_folder_service.find_subfolder(
            drive_service,
            parent_token,
            name,
        )

    def _ensure_watcher(self, task: SyncTaskItem) -> None:
        if self._config_manager.config.effective_disable_watcher:
            logger.debug("运行配置已禁用目录监听: task_id={}", task.id)
            return
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

    def _silence_path(
        self,
        task_id: str,
        path: Path,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        watcher = self._watchers.get(task_id)
        if watcher:
            watcher.silence(path, ttl_seconds=ttl_seconds)

    async def _list_folder_tokens(
        self, drive_service: DriveService, folder_token: str
    ) -> set[str]:
        return await self._cloud_folder_service.list_folder_tokens(
            drive_service,
            folder_token,
        )

    async def _list_files_all(
        self, drive_service: DriveService, folder_token: str
    ) -> list[DriveFile]:
        return await self._cloud_folder_service.list_files_all(drive_service, folder_token)

    async def _find_existing_doc_by_name(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
    ) -> str | None:
        return await self._cloud_folder_service.find_existing_doc_by_name(
            drive_service=drive_service,
            folder_token=folder_token,
            expected_name=expected_name,
            parse_mtime=_parse_mtime,
        )

    async def _wait_for_imported_doc(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
        existing_tokens: set[str],
    ) -> DriveFile | None:
        return await self._cloud_folder_service.wait_for_imported_doc(
            drive_service=drive_service,
            folder_token=folder_token,
            expected_name=expected_name,
            existing_tokens=existing_tokens,
            poll_attempts=self._import_poll_attempts,
            poll_interval=self._import_poll_interval,
        )

    @staticmethod
    def _resolve_created_doc_mtime(
        created_doc: DriveFile, fallback_local_mtime: float | None
    ) -> float:
        return SyncMarkdownCloudDocService.resolve_created_doc_mtime(
            created_doc,
            fallback_local_mtime,
            parse_mtime=_parse_mtime,
        )

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
        if event.is_directory:
            return
        self.queue_local_change(task.id, path, changed_at=event.timestamp)
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

    async def _sync_cloud_folder_links(
        self,
        task: SyncTaskItem,
        folders: Iterable[tuple[DriveNode, Path]],
        *,
        updated_at: float | None = None,
        create_local_dirs: bool = True,
    ) -> None:
        for node, relative_dir in folders:
            local_path = Path(task.local_path) / relative_dir
            if self._should_ignore_path(task, local_path):
                continue
            if create_local_dirs:
                self._silence_path(task.id, local_path)
                local_path.mkdir(parents=True, exist_ok=True)
            token, node_type = _resolve_target(node)
            if node_type != "folder":
                continue
            folder_mtime = (
                _parse_mtime(node.modified_time)
                if updated_at is None and node.modified_time is not None
                else updated_at
            )
            await self._link_service.upsert_link(
                local_path=str(local_path),
                cloud_token=token,
                cloud_type="folder",
                task_id=task.id,
                updated_at=folder_mtime if folder_mtime is not None else time.time(),
                cloud_parent_token=node.parent_token,
            )

    def _build_cloud_folder_paths(
        self,
        task: SyncTaskItem,
        folders: Iterable[tuple[DriveNode, Path]],
    ) -> set[str]:
        paths: set[str] = set()
        for _node, relative_dir in folders:
            local_path = Path(task.local_path) / relative_dir
            if not self._should_ignore_path(task, local_path):
                paths.add(str(local_path))
        return paths

    async def _prefill_links_from_cloud(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> None:
        tree = await drive_service.scan_folder(
            task.cloud_folder_token, name=task.name or "同步根目录"
        )
        folders = list(_flatten_folders(tree))
        await self._sync_cloud_folder_links(
            task,
            folders,
            updated_at=0.0,
            create_local_dirs=False,
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


def _flatten_folders(
    node: DriveNode, base: Path | None = None
) -> Iterable[tuple[DriveNode, Path]]:
    base = base or Path()
    for child in node.children:
        if child.type != "folder":
            continue
        if child.name == _CLOUD_MD_MIRROR_FOLDER_NAME:
            continue
        relative_dir = base / sanitize_path_segment(child.name)
        yield child, relative_dir
        yield from _flatten_folders(child, relative_dir)


def _folder_cloud_tokens(folders: Iterable[tuple[DriveNode, Path]]) -> set[str]:
    tokens: set[str] = set()
    for node, _relative_dir in folders:
        token, node_type = _resolve_target(node)
        if node_type == "folder" and token:
            tokens.add(token)
    return tokens


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


def _has_local_image_upload_revision(revision: str | None) -> bool:
    return bool(revision and _LOCAL_IMAGE_UPLOAD_REVISION_MARKER in revision)


def _has_markdown_table_render_revision(revision: str | None) -> bool:
    return bool(revision and _MARKDOWN_TABLE_RENDER_REVISION_MARKER in revision)


def _normalize_markdown_resource_ref(raw: str) -> str:
    ref = raw.strip()
    if ref.startswith("<") and ref.endswith(">"):
        ref = ref[1:-1].strip()
    return re.sub(r"""\s+(?:"[^"]*"|'[^']*'|\([^()]*\))\s*$""", "", ref)


def _is_uploadable_markdown_image_ref(
    ref: str, base_path: str | Path | None
) -> bool:
    lowered = ref.strip().lower()
    if lowered.startswith("data:image/"):
        return True
    if _is_remote_or_anchor_resource(lowered):
        return False
    path = _resolve_markdown_resource_path(ref, base_path)
    return path.exists() and path.is_file()


def _is_remote_or_anchor_resource(lowered_ref: str) -> bool:
    return (
        lowered_ref.startswith("http://")
        or lowered_ref.startswith("https://")
        or lowered_ref.startswith("mailto:")
        or lowered_ref.startswith("tel:")
        or lowered_ref.startswith("#")
    )


def _resolve_markdown_resource_path(ref: str, base_path: str | Path | None) -> Path:
    normalized = ref.strip()
    parsed = urlparse(normalized)
    if parsed.scheme.lower() == "file":
        normalized = parsed.path or ""
        if parsed.netloc:
            normalized = f"//{parsed.netloc}{normalized}"
    else:
        normalized = normalized.split("#", 1)[0].split("?", 1)[0]
    normalized = unquote(normalized).replace("\\ ", " ").strip()
    if (
        normalized.startswith("/")
        and len(normalized) >= 3
        and normalized[1].isalpha()
        and normalized[2] == ":"
    ):
        normalized = normalized[1:]
    path = Path(normalized)
    if not path.is_absolute() and base_path:
        base = Path(base_path)
        if base.is_file():
            base = base.parent
        path = base / path
    return path.expanduser()


def _build_local_resource_signature_entry(
    ref: str,
    base_path: str | Path | None,
    *,
    image_only: bool,
) -> str | None:
    normalized = ref.strip()
    if not normalized:
        return None
    lowered = normalized.lower()
    if image_only and lowered.startswith("data:image/"):
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"data-image:{digest}"
    if _is_remote_or_anchor_resource(lowered):
        return None
    path = _resolve_markdown_resource_path(normalized, base_path)
    if not path.exists() or not path.is_file():
        return f"missing:{normalized}"
    try:
        stat = path.stat()
    except OSError:
        return f"stat-error:{normalized}"
    return f"{path.as_posix()}|{int(stat.st_size)}|{int(stat.st_mtime_ns)}"


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
