from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from loguru import logger

from src.services.bitable_service import BitableService
from src.services.docx_service import DocxService
from src.services.drive_service import DriveNode, DriveService
from src.services.export_task_service import ExportTaskService
from src.services.file_downloader import FileDownloader
from src.services.file_uploader import FileUploader
from src.services.sheet_service import SheetService
from src.services.sync_download_support_service import DownloadCandidate
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem
from src.services.transcoder import DocxTranscoder

FlattenFoldersFn = Callable[[DriveNode], Iterable[Any]]
FlattenFilesFn = Callable[[DriveNode], Iterable[Any]]
BuildLinkMapFn = Callable[[list[Any], str], dict[str, Path]]
MergeSyncedLinkMapFn = Callable[[dict[str, Path], list[SyncLinkItem]], dict[str, Path]]
FolderCloudTokensFn = Callable[[list[Any]], set[str]]
SyncCloudFolderLinksFn = Callable[[SyncTaskItem, list[Any]], Awaitable[None]]
BuildDownloadCandidateFn = Callable[[SyncTaskItem, DriveNode, Path], DownloadCandidate]
HydrateExportSubIdsFn = Callable[..., Awaitable[list[DownloadCandidate]]]
ShouldIgnorePathFn = Callable[[SyncTaskItem, Path], bool]
SelectDownloadCandidatesFn = Callable[[list[DownloadCandidate], dict[str, SyncLinkItem]], tuple[list[DownloadCandidate], list[DownloadCandidate]]]
MatchesDownloadSelectionFn = Callable[..., bool]
BuildCloudFolderPathsFn = Callable[[SyncTaskItem, list[Any]], set[str]]
EnqueueCloudMissingDeletesFn = Callable[..., Awaitable[None]]
RecordEventFn = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]
ShouldSkipDownloadForLocalNewerFn = Callable[..., bool]
ShouldSkipDownloadForUnchangedFn = Callable[..., bool]
DownloadDocxFn = Callable[..., Awaitable[str]]
GetLocalSignatureFn = Callable[[Path], tuple[str, int, float] | None]
BuildCloudRevisionFn = Callable[[str, float, str | None], str]
CalculateLocalResourceSignatureFn = Callable[[str, Path], str | None]
RebuildBlockStateFn = Callable[..., Awaitable[None]]
ShouldSyncMdCloudMirrorFn = Callable[[SyncTaskItem], bool]
SyncMarkdownMirrorCopyFn = Callable[..., Awaitable[None]]
SilencePathFn = Callable[[str, Path], None]
ProcessPendingDeletesFn = Callable[..., Awaitable[None]]
WriteMarkdownFn = Callable[[Path, str, float], None]
DownloadExportedFileFn = Callable[..., Awaitable[None]]


@dataclass
class DownloadRuntimeServices:
    drive_service: DriveService
    docx_service: DocxService
    sheet_service: SheetService
    transcoder: DocxTranscoder
    file_downloader: FileDownloader
    file_uploader: FileUploader
    export_task_service: ExportTaskService
    bitable_service: BitableService
    link_service: SyncLinkService
    owned_services: list[Any]


class SyncDownloadOrchestrationService:
    def __init__(
        self,
        *,
        export_extension_map: dict[str, str],
        flatten_folders: FlattenFoldersFn,
        flatten_files: FlattenFilesFn,
        build_link_map: BuildLinkMapFn,
        merge_synced_link_map: MergeSyncedLinkMapFn,
        folder_cloud_tokens: FolderCloudTokensFn,
        sync_cloud_folder_links: SyncCloudFolderLinksFn,
        build_download_candidate: BuildDownloadCandidateFn,
        hydrate_export_sub_ids: HydrateExportSubIdsFn,
        should_ignore_path: ShouldIgnorePathFn,
        select_download_candidates: SelectDownloadCandidatesFn,
        matches_download_selection: MatchesDownloadSelectionFn,
        build_cloud_folder_paths: BuildCloudFolderPathsFn,
        enqueue_cloud_missing_deletes: EnqueueCloudMissingDeletesFn,
        record_event: RecordEventFn,
        should_skip_download_for_local_newer: ShouldSkipDownloadForLocalNewerFn,
        should_skip_download_for_unchanged: ShouldSkipDownloadForUnchangedFn,
        download_docx: DownloadDocxFn,
        download_exported_file: DownloadExportedFileFn,
        get_local_signature: GetLocalSignatureFn,
        build_cloud_revision: BuildCloudRevisionFn,
        calculate_local_resource_signature: CalculateLocalResourceSignatureFn,
        rebuild_block_state: RebuildBlockStateFn,
        should_sync_md_cloud_mirror: ShouldSyncMdCloudMirrorFn,
        sync_markdown_mirror_copy: SyncMarkdownMirrorCopyFn,
        silence_path: SilencePathFn,
        process_pending_deletes: ProcessPendingDeletesFn,
        write_markdown: WriteMarkdownFn,
    ) -> None:
        self._export_extension_map = export_extension_map
        self._flatten_folders = flatten_folders
        self._flatten_files = flatten_files
        self._build_link_map = build_link_map
        self._merge_synced_link_map = merge_synced_link_map
        self._folder_cloud_tokens = folder_cloud_tokens
        self._sync_cloud_folder_links = sync_cloud_folder_links
        self._build_download_candidate = build_download_candidate
        self._hydrate_export_sub_ids = hydrate_export_sub_ids
        self._should_ignore_path = should_ignore_path
        self._select_download_candidates = select_download_candidates
        self._matches_download_selection = matches_download_selection
        self._build_cloud_folder_paths = build_cloud_folder_paths
        self._enqueue_cloud_missing_deletes = enqueue_cloud_missing_deletes
        self._record_event = record_event
        self._should_skip_download_for_local_newer = should_skip_download_for_local_newer
        self._should_skip_download_for_unchanged = should_skip_download_for_unchanged
        self._download_docx = download_docx
        self._download_exported_file = download_exported_file
        self._get_local_signature = get_local_signature
        self._build_cloud_revision = build_cloud_revision
        self._calculate_local_resource_signature = calculate_local_resource_signature
        self._rebuild_block_state = rebuild_block_state
        self._should_sync_md_cloud_mirror = should_sync_md_cloud_mirror
        self._sync_markdown_mirror_copy = sync_markdown_mirror_copy
        self._silence_path = silence_path
        self._process_pending_deletes = process_pending_deletes
        self._write_markdown = write_markdown

    async def run_download(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        runtime: DownloadRuntimeServices,
        allow_deletes: bool = True,
        selected_paths: set[str] | None = None,
        selected_cloud_tokens: set[str] | None = None,
        force_paths: set[str] | None = None,
    ) -> None:
        try:
            tree = await runtime.drive_service.scan_folder(
                task.cloud_folder_token, name=task.name or "同步根目录"
            )
            folders = list(self._flatten_folders(tree))
            await self._sync_cloud_folder_links(task, folders)
            files = list(self._flatten_files(tree))
            logger.debug(
                "下载阶段: task_id={} folders={} files={}",
                task.id,
                len(folders),
                len(files),
            )
            link_map = self._build_link_map(files, task.local_path)
            persisted_links = await runtime.link_service.list_by_task(task.id)
            link_map = self._merge_synced_link_map(link_map, persisted_links)
            persisted_by_path = {item.local_path: item for item in persisted_links}
            candidates = [
                self._build_download_candidate(task, node, relative_dir)
                for node, relative_dir in files
            ]
            candidates = await self._hydrate_export_sub_ids(
                candidates,
                runtime.drive_service,
                sheet_service=runtime.sheet_service,
                bitable_service=runtime.bitable_service,
            )
            candidates = [
                item for item in candidates if not self._should_ignore_path(task, item.target_path)
            ]
            selected_candidates, duplicated_candidates = self._select_download_candidates(
                candidates,
                persisted_by_path,
            )
            if selected_paths or selected_cloud_tokens:
                selected_candidates = [
                    item
                    for item in selected_candidates
                    if self._matches_download_selection(
                        item,
                        selected_paths=selected_paths,
                        selected_cloud_tokens=selected_cloud_tokens,
                    )
                ]
                duplicated_candidates = [
                    item
                    for item in duplicated_candidates
                    if self._matches_download_selection(
                        item,
                        selected_paths=selected_paths,
                        selected_cloud_tokens=selected_cloud_tokens,
                    )
                ]
            known_cloud_tokens = self._folder_cloud_tokens(folders)
            known_cloud_tokens.update(item.effective_token for item in selected_candidates)
            selected_cloud_paths = self._build_cloud_folder_paths(task, folders)
            selected_cloud_paths.update(str(item.target_path) for item in selected_candidates)
            if allow_deletes:
                await self._enqueue_cloud_missing_deletes(
                    task=task,
                    status=status,
                    persisted_links=persisted_links,
                    cloud_paths=selected_cloud_paths,
                )
            status.total_files = len(selected_candidates) + len(duplicated_candidates)

            for duplicated in duplicated_candidates:
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(
                        path=str(duplicated.target_path),
                        status="skipped",
                        message=(
                            "云端存在同名文件，已跳过重复项: "
                            f"type={duplicated.effective_type} token={duplicated.effective_token}"
                        ),
                    ),
                    None,
                )
                logger.info(
                    "跳过重复同名云端文件: task_id={} path={} type={} token={}",
                    task.id,
                    duplicated.target_path,
                    duplicated.effective_type,
                    duplicated.effective_token,
                )

            for candidate in selected_candidates:
                await self._download_candidate(
                    task=task,
                    status=status,
                    candidate=candidate,
                    runtime=runtime,
                    persisted=persisted_by_path.get(str(candidate.target_path)),
                    link_map=link_map,
                    force_paths=force_paths,
                    allow_cloud_writes=allow_deletes,
                )

            if allow_deletes:
                await self._process_pending_deletes(
                    task=task,
                    status=status,
                    drive_service=runtime.drive_service,
                    known_cloud_tokens=known_cloud_tokens,
                )
        finally:
            await self._close_owned_services(runtime)

    async def _download_candidate(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        candidate: DownloadCandidate,
        runtime: DownloadRuntimeServices,
        persisted: SyncLinkItem | None,
        link_map: dict[str, Path],
        force_paths: set[str] | None,
        allow_cloud_writes: bool,
    ) -> None:
        node = candidate.node
        effective_token = candidate.effective_token
        effective_type = candidate.effective_type
        target_dir = candidate.target_dir
        target_path = candidate.target_path
        mtime = candidate.mtime
        forced = bool(force_paths and str(target_path) in force_paths)
        if (not forced) and self._should_skip_download_for_local_newer(
            task=task,
            local_path=target_path,
            cloud_mtime=mtime,
        ):
            status.skipped_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(target_path),
                    status="skipped",
                    message="本地较新，跳过下载",
                ),
                None,
            )
            logger.info(
                "检测到本地较新文件，跳过下载: task_id={} path={} cloud_mtime={} local_mtime={}",
                task.id,
                target_path,
                mtime,
                target_path.stat().st_mtime,
            )
            return
        if (not forced) and self._should_skip_download_for_unchanged(
            local_path=target_path,
            cloud_mtime=mtime,
            persisted=persisted,
            effective_token=effective_token,
            effective_type=effective_type,
        ):
            status.skipped_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(target_path),
                    status="skipped",
                    message="云端未更新，跳过下载",
                ),
                None,
            )
            logger.info(
                "云端未更新，跳过下载: task_id={} path={} type={} token={} cloud_mtime={}",
                task.id,
                target_path,
                effective_type,
                effective_token,
                mtime,
            )
            return

        try:
            if effective_type in {"docx", "doc"}:
                await self._download_document_candidate(
                    task=task,
                    status=status,
                    candidate=candidate,
                    runtime=runtime,
                    link_map=link_map,
                    allow_cloud_writes=allow_cloud_writes,
                )
                return
            if effective_type in self._export_extension_map:
                await self._download_export_candidate(
                    task=task,
                    status=status,
                    candidate=candidate,
                    runtime=runtime,
                )
                return
            if effective_type == "file":
                await self._download_file_candidate(
                    task=task,
                    status=status,
                    candidate=candidate,
                    runtime=runtime,
                )
                return
            status.skipped_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(target_path),
                    status="skipped",
                    message=f"暂不支持类型: {effective_type}",
                ),
                None,
            )
        except Exception as exc:
            status.failed_files += 1
            status.last_error = str(exc)
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(target_path),
                    status="failed",
                    message=f"type={effective_type} token={effective_token} error={exc}",
                ),
                None,
            )
            logger.error(
                "下载失败: task_id={} path={} type={} token={} error={}",
                task.id,
                target_path,
                effective_type,
                effective_token,
                exc,
            )

    async def _download_document_candidate(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        candidate: DownloadCandidate,
        runtime: DownloadRuntimeServices,
        link_map: dict[str, Path],
        allow_cloud_writes: bool,
    ) -> None:
        node = candidate.node
        effective_token = candidate.effective_token
        target_dir = candidate.target_dir
        target_path = candidate.target_path
        mtime = candidate.mtime
        markdown = await self._download_docx(
            effective_token,
            docx_service=runtime.docx_service,
            transcoder=runtime.transcoder,
            base_dir=target_dir,
            link_map=link_map,
        )
        self._silence_path(task.id, target_path)
        self._write_markdown(target_path, markdown, mtime)
        signature = self._get_local_signature(target_path)
        cloud_revision = self._build_cloud_revision(effective_token, mtime)
        resource_signature = self._calculate_local_resource_signature(markdown, target_dir)
        await runtime.link_service.upsert_link(
            local_path=str(target_path),
            cloud_token=effective_token,
            cloud_type=candidate.effective_type,
            task_id=task.id,
            updated_at=mtime,
            cloud_parent_token=node.parent_token,
            local_hash=signature[0] if signature else None,
            local_size=signature[1] if signature else None,
            local_mtime=signature[2] if signature else None,
            cloud_revision=cloud_revision,
            cloud_mtime=mtime,
            local_resource_signature=resource_signature,
            resource_sync_revision=cloud_revision,
        )
        if task.sync_mode in {"bidirectional", "upload_only"} and ((task.update_mode or "auto") != "full"):
            await self._rebuild_block_state(
                task=task,
                docx_service=runtime.docx_service,
                document_id=effective_token,
                markdown=markdown,
                base_path=target_dir.as_posix(),
                file_path=target_path,
                user_id_type="open_id",
            )
        if allow_cloud_writes and self._should_sync_md_cloud_mirror(task):
            await self._sync_markdown_mirror_copy(
                task=task,
                status=status,
                path=target_path,
                file_uploader=runtime.file_uploader,
                drive_service=runtime.drive_service,
            )
        self._silence_path(task.id, target_path)
        status.completed_files += 1
        self._record_event(
            status,
            SyncFileEvent(path=str(target_path), status="downloaded"),
            None,
        )

    async def _download_export_candidate(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        candidate: DownloadCandidate,
        runtime: DownloadRuntimeServices,
    ) -> None:
        node = candidate.node
        effective_token = candidate.effective_token
        target_path = candidate.target_path
        mtime = candidate.mtime
        export_extension = self._export_extension_map[candidate.effective_type]
        self._silence_path(task.id, target_path)
        await self._download_exported_file(
            export_task_service=runtime.export_task_service,
            file_downloader=runtime.file_downloader,
            file_token=effective_token,
            file_type=candidate.effective_type,
            target_path=target_path,
            mtime=mtime,
            export_extension=export_extension,
            export_sub_id=candidate.export_sub_id,
        )
        signature = self._get_local_signature(target_path)
        await runtime.link_service.upsert_link(
            local_path=str(target_path),
            cloud_token=effective_token,
            cloud_type=candidate.effective_type,
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
        self._record_event(
            status,
            SyncFileEvent(path=str(target_path), status="downloaded"),
            None,
        )

    async def _download_file_candidate(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        candidate: DownloadCandidate,
        runtime: DownloadRuntimeServices,
    ) -> None:
        node = candidate.node
        effective_token = candidate.effective_token
        target_dir = candidate.target_dir
        target_path = candidate.target_path
        mtime = candidate.mtime
        self._silence_path(task.id, target_path)
        await runtime.file_downloader.download(
            file_token=effective_token,
            file_name=target_path.name,
            target_dir=target_dir,
            mtime=mtime,
        )
        signature = self._get_local_signature(target_path)
        await runtime.link_service.upsert_link(
            local_path=str(target_path),
            cloud_token=effective_token,
            cloud_type=candidate.effective_type,
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
        self._record_event(
            status,
            SyncFileEvent(path=str(target_path), status="downloaded"),
            None,
        )

    @staticmethod
    async def _close_owned_services(runtime: DownloadRuntimeServices) -> None:
        for service in runtime.owned_services:
            close = getattr(service, "close", None)
            if close:
                await close()


__all__ = ["DownloadRuntimeServices", "SyncDownloadOrchestrationService"]
