from __future__ import annotations

import asyncio
import difflib
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from loguru import logger

from src.services.docx_service import DocxService
from src.services.drive_service import DriveFile, DriveNode, DriveService
from src.services.file_downloader import FileDownloader
from src.services.file_hash import calculate_file_hash
from src.services.file_uploader import FileUploader
from src.services.file_writer import FileWriter
from src.services.markdown_blocks import hash_block, split_markdown_blocks
from src.services.import_task_service import ImportTaskError, ImportTaskService
from src.services.sync_block_service import BlockStateItem, SyncBlockService
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_task_service import SyncTaskItem
from src.services.transcoder import DocxTranscoder
from src.services.watcher import FileChangeEvent, WatcherService

SyncState = Literal["idle", "running", "success", "failed", "cancelled"]
SYNC_LOG_LIMIT = 200


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
        import_task_service: ImportTaskService | None = None,
        import_poll_attempts: int = 10,
        import_poll_interval: float = 1.0,
    ) -> None:
        self._drive_service = drive_service
        self._docx_service = docx_service
        self._transcoder = transcoder
        self._file_downloader = file_downloader
        self._file_uploader = file_uploader
        self._file_writer = file_writer or FileWriter()
        self._link_service = link_service or SyncLinkService()
        self._block_service = SyncBlockService()
        self._import_task_service = import_task_service
        self._import_poll_attempts = max(1, import_poll_attempts)
        self._import_poll_interval = max(0.0, import_poll_interval)
        self._statuses: dict[str, SyncTaskStatus] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._watchers: dict[str, WatcherService] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._uploading_paths: set[str] = set()
        self._doc_locks: dict[str, asyncio.Lock] = {}

    def get_status(self, task_id: str) -> SyncTaskStatus:
        return self._statuses.get(task_id) or SyncTaskStatus(task_id=task_id)

    def list_statuses(self) -> dict[str, SyncTaskStatus]:
        return dict(self._statuses)

    def start_task(self, task: SyncTaskItem) -> SyncTaskStatus:
        current = self._statuses.get(task.id)
        if current and current.state == "running":
            return current
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        status.state = "running"
        status.started_at = time.time()
        status.finished_at = None
        status.total_files = 0
        status.completed_files = 0
        status.failed_files = 0
        status.skipped_files = 0
        status.last_error = None
        status.last_files = []
        status.record_event(
            SyncFileEvent(
                path=task.local_path,
                status="started",
                message=f"任务启动: mode={task.sync_mode} update={task.update_mode or 'auto'}",
            )
        )
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
        self._stop_watcher(task_id)

    async def run_task(self, task: SyncTaskItem) -> None:
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
            status.record_event(
                SyncFileEvent(
                    path=task.local_path,
                    status=status.state,
                    message=message,
                )
            )
            self._tasks.pop(task.id, None)

    async def _run_download(self, task: SyncTaskItem, status: SyncTaskStatus) -> None:
        drive_service = self._drive_service or DriveService()
        docx_service = self._docx_service or DocxService()
        transcoder = self._transcoder or DocxTranscoder()
        file_downloader = self._file_downloader or FileDownloader()
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

        try:
            tree = await drive_service.scan_folder(
                task.cloud_folder_token, name=task.name or "同步根目录"
            )
            files = list(_flatten_files(tree))
            logger.info(
                "下载阶段: task_id={} files={}", task.id, len(files)
            )
            link_map = _build_link_map(files, task.local_path)
            persisted_links = await link_service.list_all()
            link_map = _merge_synced_link_map(link_map, persisted_links)
            status.total_files = len(files)

            for node, relative_dir in files:
                effective_token, effective_type = _resolve_target(node)
                target_dir = Path(task.local_path) / relative_dir
                mtime = _parse_mtime(node.modified_time)
                target_path = (
                    target_dir / _docx_filename(node.name)
                    if effective_type in {"docx", "doc"}
                    else target_dir / node.name
                )
                if self._should_skip_download_for_local_newer(
                    task=task,
                    local_path=target_path,
                    cloud_mtime=mtime,
                ):
                    status.skipped_files += 1
                    status.record_event(
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
                try:
                    if effective_type in {"docx", "doc"}:
                        markdown = await self._download_docx(
                            effective_token,
                            docx_service=docx_service,
                            transcoder=transcoder,
                            base_dir=target_dir,
                            link_map=link_map,
                        )
                        filename = _docx_filename(node.name)
                        self._file_writer.write_markdown(
                            target_dir / filename, markdown, mtime
                        )
                        await link_service.upsert_link(
                            local_path=str(target_dir / filename),
                            cloud_token=effective_token,
                            cloud_type=effective_type,
                            task_id=task.id,
                            updated_at=mtime,
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
                                file_path=target_dir / filename,
                                user_id_type="open_id",
                            )
                        self._silence_path(task.id, target_dir / filename)
                        status.completed_files += 1
                        status.record_event(
                            SyncFileEvent(
                                path=str(target_dir / filename), status="downloaded"
                            )
                        )
                    elif effective_type == "file":
                        await file_downloader.download(
                            file_token=effective_token,
                            file_name=node.name,
                            target_dir=target_dir,
                            mtime=mtime,
                        )
                        await link_service.upsert_link(
                            local_path=str(target_dir / node.name),
                            cloud_token=effective_token,
                            cloud_type=effective_type,
                            task_id=task.id,
                            updated_at=mtime,
                        )
                        self._silence_path(task.id, target_dir / node.name)
                        status.completed_files += 1
                        status.record_event(
                            SyncFileEvent(
                                path=str(target_dir / node.name), status="downloaded"
                            )
                        )
                    else:
                        status.skipped_files += 1
                        status.record_event(
                            SyncFileEvent(
                                path=str(target_dir / node.name),
                                status="skipped",
                                message=f"暂不支持类型: {effective_type}",
                            )
                        )
                except Exception as exc:
                    status.failed_files += 1
                    status.last_error = str(exc)
                    status.record_event(
                        SyncFileEvent(
                            path=str(target_dir / node.name),
                            status="failed",
                            message=f"type={effective_type} token={effective_token} error={exc}",
                        )
                    )
                    logger.error(
                        "下载失败: task_id={} path={} type={} token={} error={}",
                        task.id,
                        target_dir / node.name,
                        effective_type,
                        effective_token,
                        exc,
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

    async def _run_upload(self, task: SyncTaskItem, status: SyncTaskStatus) -> None:
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
                    status.record_event(
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
            status.record_event(
                SyncFileEvent(path=key, status="skipped", message="上传中，跳过重复触发")
            )
            logger.info("重复上传触发，已跳过: task_id={} path={}", task.id, key)
            return
        self._uploading_paths.add(key)
        try:
            if self._should_ignore_path(task, path):
                status.skipped_files += 1
                status.record_event(
                    SyncFileEvent(path=key, status="skipped", message="忽略内部目录")
                )
                return
            if not path.exists() or not path.is_file():
                return
            suffix = path.suffix.lower()
            if suffix == ".md":
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
            await self._upload_file(task, status, path, file_uploader)
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
            await self._upload_file(task, status, path, file_uploader)
            return
        created_doc = False
        if not link:
            link = await self._create_cloud_doc_for_markdown(
                task=task,
                status=status,
                path=path,
                file_uploader=file_uploader,
                drive_service=drive_service,
                import_task_service=import_task_service,
            )
            if not link:
                status.failed_files += 1
                status.record_event(
                    SyncFileEvent(
                        path=str(path),
                        status="failed",
                        message="创建云端文档失败",
                    )
                )
                return
            created_doc = True
        base_path = path.parent.as_posix()
        mtime = path.stat().st_mtime
        file_hash = calculate_file_hash(path)
        block_states = await self._block_service.list_blocks(str(path), link.cloud_token)
        if block_states:
            if all(item.file_hash == file_hash for item in block_states):
                status.skipped_files += 1
                status.record_event(
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化")
                )
                return
        else:
            if task.sync_mode != "upload_only" and mtime <= (link.updated_at + 1.0):
                status.skipped_files += 1
                status.record_event(
                    SyncFileEvent(path=str(path), status="skipped", message="本地未变更")
                )
                return
        if link.cloud_type not in {"docx", "doc"}:
            status.failed_files += 1
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持 Markdown 覆盖: {link.cloud_type}",
                )
            )
            return
        lock = self._doc_locks.setdefault(link.cloud_token, asyncio.Lock())
        async with lock:
            markdown = path.read_text(encoding="utf-8")
            logger.info(
                "上传文档: task_id={} path={} token={}",
                task.id,
                path,
                link.cloud_token,
            )
            if created_doc:
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
                update_mode = task.update_mode or "auto"
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
        await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=link.cloud_token,
            cloud_type=link.cloud_type,
            task_id=task.id,
            updated_at=mtime,
        )
        status.completed_files += 1
        status.record_event(SyncFileEvent(path=str(path), status="uploaded"))
        logger.info("上传完成: task_id={} path={}", task.id, path)

    async def _upload_file(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        mtime = path.stat().st_mtime
        if task.sync_mode != "upload_only" and link and mtime <= (link.updated_at + 1.0):
            status.skipped_files += 1
            status.record_event(
                SyncFileEvent(path=str(path), status="skipped", message="本地未变更")
            )
            return
        if link and link.cloud_type != "file":
            status.failed_files += 1
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持文件上传: {link.cloud_type}",
                )
            )
            return
        logger.info("上传文件: task_id={} path={}", task.id, path)
        result = await file_uploader.upload_file(
            file_path=path,
            parent_node=task.cloud_folder_token,
            parent_type="explorer",
        )
        await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=result.file_token,
            cloud_type="file",
            task_id=task.id,
            updated_at=mtime,
        )
        status.completed_files += 1
        status.record_event(SyncFileEvent(path=str(path), status="uploaded"))

    async def _create_cloud_doc_for_markdown(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
        drive_service: DriveService,
        import_task_service: ImportTaskService,
    ) -> SyncLinkItem | None:
        suffix = path.suffix.lower().lstrip(".")
        if not suffix:
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="Markdown 文件缺少扩展名",
                )
            )
            return None
        status.record_event(
            SyncFileEvent(path=str(path), status="creating", message="创建云端文档")
        )
        existing_tokens = await self._list_folder_tokens(
            drive_service, task.cloud_folder_token
        )
        try:
            upload = await file_uploader.upload_file(
                file_path=path,
                parent_node=task.cloud_folder_token,
                parent_type="explorer",
                record_db=False,
            )
            await import_task_service.create_import_task(
                file_extension=suffix,
                file_token=upload.file_token,
                mount_key=task.cloud_folder_token,
                file_name=path.stem,
                doc_type="docx",
            )
        except ImportTaskError as exc:
            status.record_event(
                SyncFileEvent(path=str(path), status="failed", message=str(exc))
            )
            return None
        except Exception as exc:
            status.record_event(
                SyncFileEvent(path=str(path), status="failed", message=str(exc))
            )
            return None

        doc_token = await self._wait_for_imported_doc(
            drive_service=drive_service,
            folder_token=task.cloud_folder_token,
            expected_name=path.stem,
            existing_tokens=existing_tokens,
        )
        if not doc_token:
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="导入任务完成但未找到新文档",
                )
            )
            return None

        link = await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=doc_token,
            cloud_type="docx",
            task_id=task.id,
            updated_at=0.0,
        )
        status.record_event(
            SyncFileEvent(path=str(path), status="created", message="云端文档已创建")
        )
        return link

    def _iter_local_files(self, task: SyncTaskItem) -> Iterable[Path]:
        root = Path(task.local_path)
        if not root.exists():
            return []
        return [path for path in root.rglob("*") if path.is_file()]

    def _should_ignore_path(self, task: SyncTaskItem, path: Path) -> bool:
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return True
        lowered = {part.lower() for part in relative.parts}
        if "assets" in lowered or "attachments" in lowered:
            return True
        return False

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
        if event.event_type == "deleted":
            return
        path = Path(event.dest_path or event.src_path)
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
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
            status.record_event(
                SyncFileEvent(path=str(path), status="failed", message=str(exc))
            )
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

    async def _apply_block_update(
        self,
        *,
        task: SyncTaskItem,
        docx_service: DocxService,
        document_id: str,
        markdown: str,
        base_path: str,
        file_path: Path,
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
                raise RuntimeError("块级映射不一致，无法局部更新")
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
            if node_type not in {"docx", "doc", "file"}:
                continue
            target_dir = Path(task.local_path) / relative_dir
            local_path = (
                target_dir / _docx_filename(node.name)
                if node_type in {"docx", "doc"}
                else target_dir / node.name
            )
            await self._link_service.upsert_link(
                local_path=str(local_path),
                cloud_token=token,
                cloud_type=node_type,
                task_id=task.id,
                updated_at=0.0,
            )

def _flatten_files(node: DriveNode, base: Path | None = None) -> Iterable[tuple[DriveNode, Path]]:
    base = base or Path()
    for child in node.children:
        if child.type == "folder":
            yield from _flatten_files(child, base / child.name)
        else:
            yield child, base


def _docx_filename(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".md"):
        return name
    if lower.endswith(".docx") or lower.endswith(".doc"):
        return f"{Path(name).stem}.md"
    return f"{name}.md"


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
        elif node_type == "file":
            mapping[token] = target_dir / node.name
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
