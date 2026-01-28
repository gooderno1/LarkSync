from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from src.services.docx_service import DocxService
from src.services.drive_service import DriveNode, DriveService
from src.services.file_downloader import FileDownloader
from src.services.file_writer import FileWriter
from src.services.sync_task_service import SyncTaskItem
from src.services.transcoder import DocxTranscoder

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
        file_writer: FileWriter | None = None,
    ) -> None:
        self._drive_service = drive_service
        self._docx_service = docx_service
        self._transcoder = transcoder
        self._file_downloader = file_downloader
        self._file_writer = file_writer or FileWriter()
        self._statuses: dict[str, SyncTaskStatus] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def get_status(self, task_id: str) -> SyncTaskStatus:
        return self._statuses.get(task_id) or SyncTaskStatus(task_id=task_id)

    def list_statuses(self) -> dict[str, SyncTaskStatus]:
        return dict(self._statuses)

    def start_task(self, task: SyncTaskItem) -> SyncTaskStatus:
        current = self._statuses.get(task.id)
        if current and current.state == "running":
            return current
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
        self._tasks[task.id] = asyncio.create_task(self.run_task(task))
        return status

    def cancel_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()

    async def run_task(self, task: SyncTaskItem) -> None:
        status = self._statuses.setdefault(task.id, SyncTaskStatus(task_id=task.id))
        try:
            if task.sync_mode != "download_only":
                status.state = "failed"
                status.last_error = "当前仅支持 download_only 模式执行下载"
                status.finished_at = time.time()
                return
            await self._run_download(task, status)
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
            status.total_files = len(files)

            for node, relative_dir in files:
                target_dir = Path(task.local_path) / relative_dir
                mtime = _parse_mtime(node.modified_time)
                try:
                    if node.type == "docx":
                        markdown = await self._download_docx(
                            node.token,
                            docx_service=docx_service,
                            transcoder=transcoder,
                        )
                        filename = _docx_filename(node.name)
                        self._file_writer.write_markdown(
                            target_dir / filename, markdown, mtime
                        )
                        status.completed_files += 1
                        status.record_event(
                            SyncFileEvent(
                                path=str(target_dir / filename), status="downloaded"
                            )
                        )
                    else:
                        await file_downloader.download(
                            file_token=node.token,
                            file_name=node.name,
                            target_dir=target_dir,
                            mtime=mtime,
                        )
                        status.completed_files += 1
                        status.record_event(
                            SyncFileEvent(
                                path=str(target_dir / node.name), status="downloaded"
                            )
                        )
                except Exception as exc:
                    status.failed_files += 1
                    status.last_error = str(exc)
                    status.record_event(
                        SyncFileEvent(
                            path=str(target_dir / node.name),
                            status="failed",
                            message=str(exc),
                        )
                    )
        finally:
            for service in owned_services:
                close = getattr(service, "close", None)
                if close:
                    await close()

    async def _download_docx(
        self, document_id: str, *, docx_service: DocxService, transcoder: DocxTranscoder
    ) -> str:
        blocks = await docx_service.list_blocks(document_id)
        return await transcoder.to_markdown(document_id, blocks)

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


__all__ = ["SyncTaskRunner", "SyncTaskStatus", "SyncFileEvent"]
