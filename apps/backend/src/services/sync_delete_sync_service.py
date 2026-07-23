from __future__ import annotations

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger

from src.core.config import ConfigManager, DeletePolicy
from src.services.drive_service import DriveService
from src.services.sync_block_service import SyncBlockService
from src.services.sync_link_service import SyncLinkItem, SyncLinkService
from src.services.sync_runner_state import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem
from src.services.sync_tombstone_service import SyncTombstoneService

ShouldIgnorePath = Callable[[SyncTaskItem, Path], bool]
RecordEvent = Callable[[SyncTaskStatus, SyncFileEvent, SyncTaskItem | None], None]
CleanupMdMirror = Callable[..., Awaitable[None]]
SilencePath = Callable[..., None]


class SyncDeleteSyncService:
    def __init__(
        self,
        *,
        link_service: SyncLinkService,
        tombstone_service: SyncTombstoneService,
        block_service: SyncBlockService,
        should_ignore_path: ShouldIgnorePath,
        local_trash_dir_name: str,
    ) -> None:
        self._link_service = link_service
        self._tombstone_service = tombstone_service
        self._block_service = block_service
        self._should_ignore_path = should_ignore_path
        self._local_trash_dir_name = local_trash_dir_name

    @staticmethod
    def normalize_delete_policy(raw_policy: object) -> DeletePolicy:
        if isinstance(raw_policy, DeletePolicy):
            return raw_policy
        try:
            return DeletePolicy(str(raw_policy))
        except ValueError:
            return DeletePolicy.safe

    def resolve_delete_policy(
        self, task: SyncTaskItem | None = None
    ) -> tuple[DeletePolicy, float]:
        config = ConfigManager.get().config
        policy_raw: object = config.delete_policy
        grace_raw: object = config.delete_grace_minutes
        if task is not None:
            if task.delete_policy:
                policy_raw = task.delete_policy
            if task.delete_grace_minutes is not None:
                grace_raw = task.delete_grace_minutes
        policy = self.normalize_delete_policy(policy_raw)
        grace_minutes = int(grace_raw or 0)
        if grace_minutes < 0:
            grace_minutes = 0
        grace_seconds = float(grace_minutes * 60)
        if policy == DeletePolicy.strict:
            grace_seconds = 0.0
        return policy, grace_seconds

    async def has_pending_tombstones(self, task_id: str) -> bool:
        try:
            pending = await self._tombstone_service.list_pending(
                task_id,
                before=time.time(),
            )
        except Exception:
            logger.exception("读取删除墓碑失败: task_id={}", task_id)
            return False
        return bool(pending)

    async def enqueue_local_delete_tombstone(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        local_path: Path,
        reason: str,
        record_event: RecordEvent,
    ) -> bool:
        policy, grace_seconds = self.resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return False
        if self.normalize_local_path_key(local_path) == self.normalize_local_path_key(
            task.local_path
        ):
            logger.warning("忽略同步根目录删除事件: task_id={} path={}", task.id, local_path)
            return False
        link = await self._link_service.get_by_local_path(str(local_path))
        if not link:
            return False
        expire_at = time.time() + grace_seconds
        try:
            tombstone = await self._tombstone_service.create_or_refresh(
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
        if not getattr(tombstone, "created", True):
            return False
        record_event(
            status,
            SyncFileEvent(
                path=str(local_path),
                status="delete_pending",
                message=f"{reason}，待处理删除同步",
            ),
            task,
        )
        return True

    async def enqueue_missing_local_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        record_event: RecordEvent,
    ) -> None:
        policy, grace_seconds = self.resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return
        root = Path(task.local_path)
        if not root.exists() or not root.is_dir():
            logger.warning(
                "同步根目录不存在，跳过本地缺失删除判定: task_id={} path={}",
                task.id,
                root,
            )
            return
        links = await self._link_service.list_by_task(task.id)
        if not links:
            return
        expire_at = time.time() + grace_seconds
        missing_folder_roots: list[str] = []
        sorted_links = sorted(links, key=lambda item: len(Path(item.local_path).parts))
        for link in sorted_links:
            local_path = Path(link.local_path)
            if local_path.exists():
                continue
            is_descendant_of_missing_folder = any(
                self.is_same_or_descendant_path(link.local_path, folder_root)
                and self.normalize_local_path_key(link.local_path)
                != self.normalize_local_path_key(folder_root)
                for folder_root in missing_folder_roots
            )
            if is_descendant_of_missing_folder:
                continue
            if link.updated_at <= 0 and not link.local_hash:
                continue
            try:
                tombstone = await self._tombstone_service.create_or_refresh(
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
            if getattr(tombstone, "created", True):
                record_event(
                    status,
                    SyncFileEvent(
                        path=link.local_path,
                        status="delete_pending",
                        message="检测到本地已删除，待处理删除同步",
                    ),
                    task,
                )
            if link.cloud_type == "folder":
                missing_folder_roots.append(link.local_path)

    async def enqueue_cloud_missing_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        persisted_links: list[SyncLinkItem],
        cloud_paths: set[str],
        record_event: RecordEvent,
    ) -> None:
        policy, grace_seconds = self.resolve_delete_policy(task)
        if policy == DeletePolicy.off:
            return
        expire_at = time.time() + grace_seconds
        cloud_path_keys = {self.normalize_local_path_key(path) for path in cloud_paths}
        missing_folder_roots: list[str] = []
        sorted_links = sorted(
            persisted_links,
            key=lambda item: len(Path(item.local_path).parts),
        )
        for link in sorted_links:
            if self._should_ignore_path(task, Path(link.local_path)):
                continue
            if self.normalize_local_path_key(link.local_path) in cloud_path_keys:
                continue
            is_descendant_of_missing_folder = any(
                self.is_same_or_descendant_path(link.local_path, folder_root)
                and self.normalize_local_path_key(link.local_path)
                != self.normalize_local_path_key(folder_root)
                for folder_root in missing_folder_roots
            )
            if is_descendant_of_missing_folder:
                continue
            try:
                tombstone = await self._tombstone_service.create_or_refresh(
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
            if getattr(tombstone, "created", True):
                record_event(
                    status,
                    SyncFileEvent(
                        path=link.local_path,
                        status="delete_pending",
                        message="检测到云端已删除，待处理本地删除",
                    ),
                    task,
                )
            if link.cloud_type == "folder":
                missing_folder_roots.append(link.local_path)

    async def process_pending_deletes(
        self,
        *,
        task: SyncTaskItem,
        status: SyncTaskStatus,
        drive_service: DriveService,
        record_event: RecordEvent,
        cleanup_md_mirror_copy: CleanupMdMirror,
        silence_path: SilencePath,
        known_cloud_tokens: set[str] | None = None,
    ) -> None:
        retry_delay_seconds = 300.0
        policy, _ = self.resolve_delete_policy(task)
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
                if self._should_ignore_path(task, local_path):
                    await self._tombstone_service.mark_status(
                        tombstone.id,
                        status="cancelled",
                        reason="路径已加入忽略目录",
                    )
                    record_event(
                        status,
                        SyncFileEvent(
                            path=tombstone.local_path,
                            status="skipped",
                            message="路径已加入忽略目录，取消删除联动",
                        ),
                        task,
                    )
                    continue
                if tombstone.source == "local":
                    if local_path.exists():
                        await self._tombstone_service.mark_status(
                            tombstone.id,
                            status="cancelled",
                            reason="本地文件已恢复",
                        )
                        continue
                    if tombstone.cloud_token:
                        active_link = await self.find_active_link_for_cloud_token(
                            task=task,
                            cloud_token=tombstone.cloud_token,
                            excluding_local_path=tombstone.local_path,
                        )
                        if active_link:
                            await self._tombstone_service.mark_status(
                                tombstone.id,
                                status="cancelled",
                                reason="云端文件仍绑定到其他本地路径",
                            )
                            record_event(
                                status,
                                SyncFileEvent(
                                    path=tombstone.local_path,
                                    status="skipped",
                                    message=f"云端文件仍绑定到其他本地路径，取消删除: {active_link.local_path}",
                                ),
                                task,
                            )
                            continue
                        if not callable(delete_file):
                            await self._tombstone_service.mark_status(
                                tombstone.id,
                                status="failed",
                                reason="当前 DriveService 不支持云端删除",
                                expire_at=time.time() + retry_delay_seconds,
                            )
                            record_event(
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
                            if self.is_cloud_already_deleted_error(exc):
                                logger.info(
                                    "云端文件已不存在，按幂等成功处理: token={} type={} path={}",
                                    tombstone.cloud_token,
                                    tombstone.cloud_type,
                                    tombstone.local_path,
                                )
                            else:
                                raise
                    await cleanup_md_mirror_copy(
                        task=task,
                        local_path=local_path,
                        drive_service=drive_service,
                    )
                    await self.cleanup_deleted_state(
                        task_id=task.id,
                        local_path=tombstone.local_path,
                        cloud_token=tombstone.cloud_token,
                        recursive=tombstone.cloud_type == "folder",
                    )
                    await self._tombstone_service.mark_status(
                        tombstone.id,
                        status="executed",
                    )
                    record_event(
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

                await cleanup_md_mirror_copy(
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
                        moved_to = self.move_to_local_trash(
                            task,
                            local_path,
                            silence_path=silence_path,
                        )
                        local_message = f"本地文件已移入回收目录: {moved_to}"
                else:
                    local_message = "本地文件已不存在"

                await self.cleanup_deleted_state(
                    task_id=task.id,
                    local_path=tombstone.local_path,
                    cloud_token=tombstone.cloud_token,
                    recursive=tombstone.cloud_type == "folder",
                )
                await self._tombstone_service.mark_status(
                    tombstone.id,
                    status="executed",
                )
                record_event(
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
                record_event(
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

    async def cleanup_deleted_state(
        self,
        *,
        task_id: str,
        local_path: str,
        cloud_token: str | None,
        recursive: bool = False,
    ) -> None:
        cleanup_targets: list[tuple[str, str | None]] = []
        if recursive:
            try:
                links = await self._link_service.list_by_task(task_id)
            except Exception:
                logger.exception("查询递归清理同步映射失败: task_id={}", task_id)
                links = []
            for link in links:
                if self.is_same_or_descendant_path(link.local_path, local_path):
                    cleanup_targets.append((link.local_path, link.cloud_token))
        if not cleanup_targets:
            link = await self._link_service.get_by_local_path(local_path)
            token = cloud_token or (link.cloud_token if link else None)
            cleanup_targets.append((local_path, token))

        seen_paths: set[str] = set()
        for target_path, target_token in cleanup_targets:
            normalized = self.normalize_local_path_key(target_path)
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            token = target_token or cloud_token
            try:
                await self._link_service.delete_by_local_path(target_path)
            except Exception:
                logger.exception("清理同步映射失败: {}", target_path)
            if token:
                try:
                    await self._block_service.replace_blocks(target_path, token, [])
                except Exception:
                    logger.exception(
                        "清理块级映射失败: path={} token={}",
                        target_path,
                        token,
                    )

    async def find_active_link_for_cloud_token(
        self,
        *,
        task: SyncTaskItem,
        cloud_token: str,
        excluding_local_path: str,
    ) -> SyncLinkItem | None:
        excluded = self.normalize_local_path_key(excluding_local_path)
        try:
            links = await self._link_service.list_by_task(task.id)
        except Exception:
            logger.exception("查询同步映射失败: task_id={} token={}", task.id, cloud_token)
            return None
        for link in links:
            if link.cloud_token != cloud_token:
                continue
            if self.normalize_local_path_key(link.local_path) == excluded:
                continue
            candidate = Path(link.local_path)
            if not candidate.exists():
                continue
            if self._should_ignore_path(task, candidate):
                continue
            return link
        return None

    @staticmethod
    def normalize_local_path_key(path: str | Path) -> str:
        return os.path.normcase(os.path.normpath(str(path)))

    @classmethod
    def is_same_or_descendant_path(
        cls,
        path: str | Path,
        ancestor: str | Path,
    ) -> bool:
        normalized_path = cls.normalize_local_path_key(path)
        normalized_ancestor = cls.normalize_local_path_key(ancestor)
        if normalized_path == normalized_ancestor:
            return True
        try:
            return (
                os.path.commonpath([normalized_path, normalized_ancestor])
                == normalized_ancestor
            )
        except ValueError:
            return False

    def move_to_local_trash(
        self,
        task: SyncTaskItem,
        local_path: Path,
        *,
        silence_path: SilencePath,
    ) -> Path:
        root = Path(task.local_path)
        trash_root = root / self._local_trash_dir_name
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
        silence_path(task.id, local_path, ttl_seconds=60.0)
        silence_path(task.id, target, ttl_seconds=60.0)
        shutil.move(str(local_path), str(target))
        return target

    @staticmethod
    def is_cloud_already_deleted_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = (
            "file has been delete",
            "file already deleted",
            "file not found",
            "resource not found",
            "not found. token=",
            "not exist",
        )
        return any(marker in lowered for marker in markers)


__all__ = ["SyncDeleteSyncService"]
