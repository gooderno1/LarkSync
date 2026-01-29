from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from src.services.docx_service import DocxService
from src.services.drive_service import DriveNode, DriveService
from src.services.file_downloader import FileDownloader
from src.services.file_uploader import FileUploader
from src.services.file_writer import FileWriter
from src.services.sync_link_service import SyncLinkService
from src.services.sync_task_service import SyncTaskItem
from src.services.transcoder import DocxTranscoder
from src.services.watcher import FileChangeEvent, WatcherService

SyncState = Literal["idle", "running", "success", "failed", "cancelled"]


@dataclass
class SyncFileEvent:
    path: str
    status: str
    message: str | None = None


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

    def record_event(self, event: SyncFileEvent, limit: int = 20) -> None:
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
    ) -> None:
        self._drive_service = drive_service
        self._docx_service = docx_service
        self._transcoder = transcoder
        self._file_downloader = file_downloader
        self._file_uploader = file_uploader
        self._file_writer = file_writer or FileWriter()
        self._link_service = link_service or SyncLinkService()
        self._statuses: dict[str, SyncTaskStatus] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._watchers: dict[str, WatcherService] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

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
        if task.sync_mode in {"bidirectional", "upload_only"}:
            self._ensure_watcher(task)
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
            link_map = _build_link_map(files, task.local_path)
            status.total_files = len(files)

            for node, relative_dir in files:
                effective_token, effective_type = _resolve_target(node)
                target_dir = Path(task.local_path) / relative_dir
                mtime = _parse_mtime(node.modified_time)
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
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

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
        owned_services = []
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._file_uploader is None:
            owned_services.append(file_uploader)

        try:
            files = list(self._iter_local_files(task))
            status.total_files += len(files)
            for path in files:
                await self._upload_path(task, status, path, docx_service, file_uploader)
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
    ) -> None:
        if self._should_ignore_path(task, path):
            status.skipped_files += 1
            status.record_event(
                SyncFileEvent(path=str(path), status="skipped", message="忽略内部目录")
            )
            return
        if not path.exists() or not path.is_file():
            return
        suffix = path.suffix.lower()
        if suffix == ".md":
            await self._upload_markdown(task, status, path, docx_service)
            return
        await self._upload_file(task, status, path, file_uploader)

    async def _upload_markdown(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        docx_service: DocxService,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        base_path = task.base_path or task.local_path
        mtime = path.stat().st_mtime
        if not link:
            status.failed_files += 1
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="缺少云端文档映射，需提供导入接口样例以创建新文档",
                )
            )
            return
        if mtime <= (link.updated_at + 1.0):
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
        markdown = path.read_text(encoding="utf-8")
        await docx_service.replace_document_content(
            link.cloud_token,
            markdown,
            base_path=base_path,
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

    async def _upload_file(
        self,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        path: Path,
        file_uploader: FileUploader,
    ) -> None:
        link = await self._link_service.get_by_local_path(str(path))
        mtime = path.stat().st_mtime
        if link and mtime <= (link.updated_at + 1.0):
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
        if link:
            status.failed_files += 1
            status.record_event(
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message="暂不支持更新已有文件，请提供更新接口样例",
                )
            )
            return
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

    async def _handle_local_event(self, task: SyncTaskItem, event: FileChangeEvent) -> None:
        if task.sync_mode == "download_only":
            return
        if event.event_type == "deleted":
            return
        path = Path(event.dest_path or event.src_path)
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        docx_service = self._docx_service or DocxService()
        file_uploader = self._file_uploader or FileUploader()
        owned_services = []
        if self._docx_service is None:
            owned_services.append(docx_service)
        if self._file_uploader is None:
            owned_services.append(file_uploader)
        try:
            await self._upload_path(task, status, path, docx_service, file_uploader)
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
        try:
            ts = float(value)
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


__all__ = ["SyncTaskRunner", "SyncTaskStatus", "SyncFileEvent"]
