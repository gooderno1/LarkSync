from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Callable

from loguru import logger

from src.services.drive_service import DriveFile, DriveService
from src.services.sync_link_service import SyncLinkService
from src.services.sync_task_service import SyncTaskItem

ShouldIgnorePath = Callable[[SyncTaskItem, Path], bool]
SupportsMdCloudMirror = Callable[[DriveService], bool]
CloudAlreadyDeletedPredicate = Callable[[Exception], bool]


class SyncCloudFolderService:
    def __init__(
        self,
        *,
        link_service: SyncLinkService,
        should_ignore_path: ShouldIgnorePath,
        md_mirror_folder_name: str,
        md_mirror_cache_prefix: str,
    ) -> None:
        self._link_service = link_service
        self._should_ignore_path = should_ignore_path
        self._md_mirror_folder_name = md_mirror_folder_name
        self._md_mirror_cache_prefix = md_mirror_cache_prefix
        self._cache: dict[tuple[str, str], str] = {}

    @property
    def cache(self) -> dict[tuple[str, str], str]:
        return self._cache

    def replace_cache(self, cache: dict[tuple[str, str], str]) -> None:
        self._cache = dict(cache)

    async def cleanup_md_mirror_copy(
        self,
        *,
        task: SyncTaskItem,
        local_path: Path,
        drive_service: DriveService,
        supports_md_cloud_mirror: SupportsMdCloudMirror,
        is_cloud_already_deleted_error: CloudAlreadyDeletedPredicate,
    ) -> None:
        if local_path.suffix.lower() != ".md":
            return
        if not supports_md_cloud_mirror(drive_service):
            return
        delete_file = getattr(drive_service, "delete_file", None)
        if not callable(delete_file):
            return
        mirror_parent = await self.find_md_mirror_parent_no_create(
            task=task,
            path=local_path,
            drive_service=drive_service,
        )
        if not mirror_parent:
            return
        existing = await self.list_files_all(drive_service, mirror_parent)
        for item in existing:
            if item.type != "file" or item.name != local_path.name:
                continue
            try:
                await delete_file(item.token, item.type)
            except Exception as exc:
                if is_cloud_already_deleted_error(exc):
                    continue
                logger.warning(
                    "删除云端 MD 镜像失败: task_id={} path={} token={} error={}",
                    task.id,
                    local_path,
                    item.token,
                    exc,
                )

    async def find_md_mirror_parent_no_create(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str | None:
        root_token = await self.find_md_mirror_root_no_create(task, drive_service)
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
            cache_key = (task.id, f"{self._md_mirror_cache_prefix}/{accumulated}")
            cached = self._cache.get(cache_key)
            if cached:
                current_token = cached
                continue
            existing_token = await self.find_subfolder(drive_service, current_token, part)
            if not existing_token:
                return None
            self._cache[cache_key] = existing_token
            current_token = existing_token
        return current_token

    async def find_md_mirror_root_no_create(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str | None:
        cache_key = (task.id, f"{self._md_mirror_cache_prefix}/root")
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        existing = await self.find_subfolder(
            drive_service, task.cloud_folder_token, self._md_mirror_folder_name
        )
        if not existing:
            return None
        self._cache[cache_key] = existing
        return existing

    async def resolve_md_mirror_parent(
        self,
        *,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        root_token = await self.ensure_md_mirror_root(task, drive_service)
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
            cache_key = (task.id, f"{self._md_mirror_cache_prefix}/{accumulated}")
            if cache_key in self._cache:
                current_token = self._cache[cache_key]
                continue
            existing_token = await self.find_subfolder(drive_service, current_token, part)
            if existing_token:
                self._cache[cache_key] = existing_token
                current_token = existing_token
                continue
            new_token = await drive_service.create_folder(current_token, part)
            self._cache[cache_key] = new_token
            current_token = new_token
            logger.info(
                "创建云端 MD 镜像子目录: task_id={} path={} token={}",
                task.id,
                accumulated,
                new_token,
            )
        return current_token

    async def ensure_md_mirror_root(
        self, task: SyncTaskItem, drive_service: DriveService
    ) -> str:
        cache_key = (task.id, f"{self._md_mirror_cache_prefix}/root")
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        existing = await self.find_subfolder(
            drive_service, task.cloud_folder_token, self._md_mirror_folder_name
        )
        if existing:
            self._cache[cache_key] = existing
            return existing
        created = await drive_service.create_folder(
            task.cloud_folder_token, self._md_mirror_folder_name
        )
        self._cache[cache_key] = created
        logger.info(
            "创建云端 MD 镜像根目录: task_id={} token={}",
            task.id,
            created,
        )
        return created

    async def resolve_cloud_parent(
        self,
        task: SyncTaskItem,
        path: Path,
        drive_service: DriveService,
    ) -> str:
        try:
            relative = path.relative_to(Path(task.local_path))
        except ValueError:
            return task.cloud_folder_token

        parent_parts = relative.parent.parts
        if not parent_parts or parent_parts == (".",):
            return task.cloud_folder_token

        current_token = task.cloud_folder_token
        accumulated = ""
        for part in parent_parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            cache_key = (task.id, accumulated)
            parent_token = current_token
            if cache_key in self._cache:
                current_token = self._cache[cache_key]
                await self.link_local_folder(
                    task=task,
                    relative_folder=Path(accumulated),
                    cloud_token=current_token,
                    cloud_parent_token=parent_token,
                )
                continue

            existing_token = await self.find_subfolder(drive_service, current_token, part)
            if existing_token:
                self._cache[cache_key] = existing_token
                current_token = existing_token
                await self.link_local_folder(
                    task=task,
                    relative_folder=Path(accumulated),
                    cloud_token=existing_token,
                    cloud_parent_token=parent_token,
                )
                continue

            new_token = await drive_service.create_folder(current_token, part)
            self._cache[cache_key] = new_token
            current_token = new_token
            await self.link_local_folder(
                task=task,
                relative_folder=Path(accumulated),
                cloud_token=new_token,
                cloud_parent_token=parent_token,
            )
            logger.info(
                "创建云端子文件夹: task_id={} path={} token={}",
                task.id,
                accumulated,
                new_token,
            )

        return current_token

    async def link_local_folder(
        self,
        *,
        task: SyncTaskItem,
        relative_folder: Path,
        cloud_token: str,
        cloud_parent_token: str | None,
    ) -> None:
        local_path = Path(task.local_path) / relative_folder
        if self._should_ignore_path(task, local_path):
            return
        await self._link_service.upsert_link(
            local_path=str(local_path),
            cloud_token=cloud_token,
            cloud_type="folder",
            task_id=task.id,
            updated_at=time.time(),
            cloud_parent_token=cloud_parent_token,
        )

    async def find_subfolder(
        self,
        drive_service: DriveService,
        parent_token: str,
        name: str,
    ) -> str | None:
        expected_name = (name or "").strip().lower()
        page_token: str | None = None
        while True:
            result = await drive_service.list_files(parent_token, page_token=page_token)
            for item in result.files:
                if item.type == "folder" and (item.name or "").strip().lower() == expected_name:
                    return item.token
            if not result.has_more or not result.next_page_token:
                break
            page_token = result.next_page_token
        return None

    async def list_folder_tokens(
        self, drive_service: DriveService, folder_token: str
    ) -> set[str]:
        items = await self.list_files_all(drive_service, folder_token)
        return {item.token for item in items}

    async def list_files_all(
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

    async def find_existing_doc_by_name(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
        parse_mtime: Callable[[str | int | float | None], float],
    ) -> str | None:
        items = await self.list_files_all(drive_service, folder_token)
        matched = [
            item for item in items if item.type in {"docx", "doc"} and item.name == expected_name
        ]
        if not matched:
            return None
        matched.sort(key=lambda item: parse_mtime(item.modified_time), reverse=True)
        return matched[0].token

    async def wait_for_imported_doc(
        self,
        *,
        drive_service: DriveService,
        folder_token: str,
        expected_name: str,
        existing_tokens: set[str],
        poll_attempts: int,
        poll_interval: float,
    ) -> DriveFile | None:
        for attempt in range(poll_attempts):
            items = await self.list_files_all(drive_service, folder_token)
            for item in items:
                if (
                    item.name == expected_name
                    and item.type in {"docx", "doc"}
                    and item.token not in existing_tokens
                ):
                    return item
            if attempt < poll_attempts - 1:
                await asyncio.sleep(poll_interval)
        return None


__all__ = ["SyncCloudFolderService"]
