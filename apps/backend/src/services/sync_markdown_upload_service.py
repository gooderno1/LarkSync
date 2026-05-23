from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger

from src.services.docx_service import (
    DocxService,
    has_markdown_table_exceeding_create_limit,
)
from src.services.drive_service import DriveService
from src.services.file_hash import calculate_file_hash
from src.services.file_uploader import FileUploader
from src.services.import_task_service import ImportTaskService
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem

UploadFileFn = Callable[..., Awaitable[None]]
CreateCloudDocForMarkdownFn = Callable[..., Awaitable[tuple[SyncLinkItem | None, bool]]]
BlockMarkdownUploadGuardFn = Callable[..., Awaitable[bool]]
ListBlockStatesFn = Callable[[str, str], Awaitable[list]]
HasUploadableMarkdownImagesFn = Callable[[str, str | Path | None], bool]
CalculateLocalResourceSignatureFn = Callable[[str, str | Path | None], str | None]
IsLocalResourceStateSyncedFn = Callable[..., bool]
IsMarkdownTableRenderStateSyncedFn = Callable[..., bool]
ShouldReimportMarkdownDocFn = Callable[..., bool]
BootstrapBlockStateFn = Callable[..., Awaitable[None]]
ApplyBlockUpdateFn = Callable[..., Awaitable[bool]]
RebuildBlockStateFn = Callable[..., Awaitable[None]]
ReimportCloudDocForMarkdownFn = Callable[..., Awaitable[SyncLinkItem | None]]
BuildCloudRevisionFn = Callable[..., str | None]
ResolveCloudParentFn = Callable[..., Awaitable[str]]
ShouldSyncMdCloudMirrorFn = Callable[[SyncTaskItem], bool]
SyncMarkdownMirrorCopyFn = Callable[..., Awaitable[None]]
CleanupMdMirrorCopyFn = Callable[..., Awaitable[None]]
HasLocalImageRevisionFn = Callable[[str | None], bool]
HasMarkdownTableRenderRevisionFn = Callable[[str | None], bool]
RecordEventFn = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]


class SyncMarkdownUploadService:
    def __init__(
        self,
        *,
        link_service: SyncLinkService,
        doc_locks: dict[str, asyncio.Lock],
        upload_file: UploadFileFn,
        create_cloud_doc_for_markdown: CreateCloudDocForMarkdownFn,
        block_markdown_upload_when_cloud_changed: BlockMarkdownUploadGuardFn,
        list_block_states: ListBlockStatesFn,
        has_uploadable_markdown_images: HasUploadableMarkdownImagesFn,
        calculate_local_resource_signature: CalculateLocalResourceSignatureFn,
        is_local_resource_state_synced: IsLocalResourceStateSyncedFn,
        is_markdown_table_render_state_synced: IsMarkdownTableRenderStateSyncedFn,
        should_reimport_markdown_doc: ShouldReimportMarkdownDocFn,
        bootstrap_block_state: BootstrapBlockStateFn,
        apply_block_update: ApplyBlockUpdateFn,
        rebuild_block_state: RebuildBlockStateFn,
        reimport_cloud_doc_for_markdown: ReimportCloudDocForMarkdownFn,
        build_cloud_revision: BuildCloudRevisionFn,
        resolve_cloud_parent: ResolveCloudParentFn,
        should_sync_md_cloud_mirror: ShouldSyncMdCloudMirrorFn,
        sync_markdown_mirror_copy: SyncMarkdownMirrorCopyFn,
        cleanup_md_mirror_copy: CleanupMdMirrorCopyFn,
        has_local_image_revision: HasLocalImageRevisionFn,
        has_markdown_table_render_revision: HasMarkdownTableRenderRevisionFn,
        record_event: RecordEventFn,
    ) -> None:
        self._link_service = link_service
        self._doc_locks = doc_locks
        self._upload_file = upload_file
        self._create_cloud_doc_for_markdown = create_cloud_doc_for_markdown
        self._block_markdown_upload_when_cloud_changed = (
            block_markdown_upload_when_cloud_changed
        )
        self._list_block_states = list_block_states
        self._has_uploadable_markdown_images = has_uploadable_markdown_images
        self._calculate_local_resource_signature = (
            calculate_local_resource_signature
        )
        self._is_local_resource_state_synced = is_local_resource_state_synced
        self._is_markdown_table_render_state_synced = (
            is_markdown_table_render_state_synced
        )
        self._should_reimport_markdown_doc = should_reimport_markdown_doc
        self._bootstrap_block_state = bootstrap_block_state
        self._apply_block_update = apply_block_update
        self._rebuild_block_state = rebuild_block_state
        self._reimport_cloud_doc_for_markdown = reimport_cloud_doc_for_markdown
        self._build_cloud_revision = build_cloud_revision
        self._resolve_cloud_parent = resolve_cloud_parent
        self._should_sync_md_cloud_mirror = should_sync_md_cloud_mirror
        self._sync_markdown_mirror_copy = sync_markdown_mirror_copy
        self._cleanup_md_mirror_copy = cleanup_md_mirror_copy
        self._has_local_image_revision = has_local_image_revision
        self._has_markdown_table_render_revision = (
            has_markdown_table_render_revision
        )
        self._record_event = record_event

    async def upload_markdown(
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
        link = await self._link_service.get_by_local_path(str(path))
        if link and link.cloud_type == "file":
            await self._upload_file(
                task,
                status,
                path,
                file_uploader,
                drive_service,
                force=force,
            )
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
                self._record_event(
                    status,
                    SyncFileEvent(
                        path=str(path),
                        status="failed",
                        message="创建云端文档失败",
                    ),
                    task,
                )
                return

        markdown = path.read_text(encoding="utf-8")
        base_path = path.parent.as_posix()
        mtime = path.stat().st_mtime
        file_hash = calculate_file_hash(path)
        has_uploadable_images = self._has_uploadable_markdown_images(markdown, base_path)
        resource_signature = self._calculate_local_resource_signature(
            markdown,
            base_path,
        )
        update_mode = task.update_mode or "auto"
        has_large_table_over_limit = has_markdown_table_exceeding_create_limit(
            markdown,
            max_rows=8,
        )
        table_render_repair_required = (
            has_large_table_over_limit and update_mode != "partial"
        )

        if await self._block_markdown_upload_when_cloud_changed(
            task=task,
            status=status,
            path=path,
            link=link,
            file_hash=file_hash,
            markdown=markdown,
            drive_service=drive_service,
            force=force,
        ):
            return

        local_images_repaired = self._has_local_image_revision(link.cloud_revision)
        table_render_repaired = self._has_markdown_table_render_revision(
            link.cloud_revision
        )
        block_states = await self._list_block_states(str(path), link.cloud_token)
        if block_states:
            if all(item.file_hash == file_hash for item in block_states) and (
                self._is_local_resource_state_synced(
                    link=link,
                    resource_signature=resource_signature,
                    has_uploadable_images=has_uploadable_images,
                    local_images_repaired=local_images_repaired,
                )
                and self._is_markdown_table_render_state_synced(
                    repair_required=table_render_repair_required,
                    repaired=table_render_repaired,
                )
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化"),
                    task,
                )
                return
        else:
            if (
                (not imported_doc)
                and link.local_hash
                and link.local_hash == file_hash
                and self._is_local_resource_state_synced(
                    link=link,
                    resource_signature=resource_signature,
                    has_uploadable_images=has_uploadable_images,
                    local_images_repaired=local_images_repaired,
                )
                and self._is_markdown_table_render_state_synced(
                    repair_required=table_render_repair_required,
                    repaired=table_render_repaired,
                )
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="内容未变化"),
                    task,
                )
                return
            if (
                (not imported_doc)
                and (not force)
                and task.sync_mode != "upload_only"
                and self._is_markdown_table_render_state_synced(
                    repair_required=table_render_repair_required,
                    repaired=table_render_repaired,
                )
                and mtime <= (link.updated_at + 1.0)
            ):
                status.skipped_files += 1
                self._record_event(
                    status,
                    SyncFileEvent(path=str(path), status="skipped", message="本地未变更"),
                    task,
                )
                return

        requires_reimport = self._should_reimport_markdown_doc(
            markdown,
            has_uploadable_images=has_uploadable_images,
        )
        if link.cloud_type not in {"docx", "doc"}:
            status.failed_files += 1
            self._record_event(
                status,
                SyncFileEvent(
                    path=str(path),
                    status="failed",
                    message=f"云端类型不支持 Markdown 覆盖: {link.cloud_type}",
                ),
                task,
            )
            return

        if (
            (not imported_doc)
            and (not block_states)
            and update_mode in {"auto", "partial"}
        ):
            await self._bootstrap_block_state(
                path=path,
                cloud_token=link.cloud_token,
                docx_service=docx_service,
                status=status,
            )

        lock = self._doc_locks.setdefault(link.cloud_token, asyncio.Lock())
        markdown_tables_rendered = False
        async with lock:
            logger.info(
                "上传文档: task_id={} path={} token={}",
                task.id,
                path,
                link.cloud_token,
            )
            if imported_doc:
                if has_uploadable_images or table_render_repair_required:
                    logger.info(
                        "导入创建后检测到需转换器修复的 Markdown 内容，改用块级覆盖: task_id={} path={} token={} has_images={} large_table={}",
                        task.id,
                        path,
                        link.cloud_token,
                        has_uploadable_images,
                        has_large_table_over_limit,
                    )
                    await docx_service.replace_document_content(
                        link.cloud_token,
                        markdown,
                        base_path=base_path,
                        update_mode="full",
                    )
                    markdown_tables_rendered = table_render_repair_required
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
                force_full_replace = (
                    table_render_repair_required and update_mode == "auto"
                )
                if force_full_replace:
                    logger.info(
                        "检测到超限表格，跳过局部更新并执行同 token 全量重建: task_id={} path={} token={} update_mode={}",
                        task.id,
                        path,
                        link.cloud_token,
                        update_mode,
                    )
                if update_mode in {"auto", "partial"} and not force_full_replace:
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
                    except RuntimeError as exc:
                        logger.info(
                            "块级更新失败，准备回退: task_id={} path={} token={} error={}",
                            task.id,
                            path,
                            link.cloud_token,
                            exc,
                        )
                        if update_mode == "partial":
                            raise
                if not applied:
                    if update_mode == "partial":
                        raise RuntimeError("partial 模式要求块级更新，但未产生可应用差异")
                    try:
                        await docx_service.replace_document_content(
                            link.cloud_token,
                            markdown,
                            base_path=base_path,
                            update_mode="full",
                        )
                        markdown_tables_rendered = table_render_repair_required
                    except Exception:
                        if not requires_reimport:
                            raise
                        logger.warning(
                            "超限表格同 token 覆盖失败，改用导入重建: task_id={} path={} token={}",
                            task.id,
                            path,
                            link.cloud_token,
                        )
                        new_link = await self._reimport_cloud_doc_for_markdown(
                            task=task,
                            status=status,
                            path=path,
                            old_link=link,
                            file_uploader=file_uploader,
                            drive_service=drive_service,
                            import_task_service=import_task_service,
                        )
                        if not new_link:
                            raise RuntimeError("导入重建云端文档失败")
                        link = new_link
                        imported_doc = True
                    else:
                        await self._rebuild_block_state(
                            task=task,
                            docx_service=docx_service,
                            document_id=link.cloud_token,
                            markdown=markdown,
                            base_path=base_path,
                            file_path=path,
                            user_id_type="open_id",
                        )
                if imported_doc:
                    if has_uploadable_images:
                        logger.info(
                            "导入创建后检测到本地图片，改用块级覆盖: task_id={} path={} token={}",
                            task.id,
                            path,
                            link.cloud_token,
                        )
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
        cloud_revision = self._build_cloud_revision(
            link.cloud_token,
            synced_at,
            local_images_uploaded=has_uploadable_images,
            markdown_tables_rendered=markdown_tables_rendered,
        )
        upload_parent = await self._resolve_cloud_parent(task, path, drive_service)
        stat = path.stat()
        await self._link_service.upsert_link(
            local_path=str(path),
            cloud_token=link.cloud_token,
            cloud_type=link.cloud_type,
            task_id=task.id,
            updated_at=synced_at,
            cloud_parent_token=upload_parent,
            local_hash=file_hash,
            local_size=stat.st_size,
            local_mtime=stat.st_mtime,
            cloud_revision=cloud_revision,
            cloud_mtime=synced_at,
            local_resource_signature=resource_signature,
            resource_sync_revision=cloud_revision,
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
        self._record_event(status, SyncFileEvent(path=str(path), status="uploaded"), task)
        logger.info("上传完成: task_id={} path={}", task.id, path)


__all__ = ["SyncMarkdownUploadService"]
