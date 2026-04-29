from __future__ import annotations

from pathlib import Path

from src.services.conflict_service import ConflictItem, ConflictService
from src.services.sync_link_service import SyncLinkService
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskItem, SyncTaskService


class ConflictResolutionError(RuntimeError):
    pass


class ConflictResolutionService:
    def __init__(
        self,
        *,
        conflict_service: ConflictService | None = None,
        task_service: SyncTaskService | None = None,
        link_service: SyncLinkService | None = None,
    ) -> None:
        self._conflict_service = conflict_service or ConflictService()
        self._task_service = task_service or SyncTaskService()
        self._link_service = link_service or SyncLinkService()

    async def resolve_conflict(
        self,
        conflict_id: str,
        action: str,
        *,
        runner: SyncTaskRunner | None,
    ) -> ConflictItem | None:
        if runner is None:
            raise ConflictResolutionError("同步执行器不可用")
        conflict = await self._conflict_service.get_conflict(conflict_id)
        if not conflict:
            return None
        task = await self._resolve_task_for_conflict(conflict)
        if task is None:
            raise ConflictResolutionError("未找到关联同步任务")
        path = Path(conflict.local_path)
        try:
            if action == "use_local":
                await runner.run_conflict_upload(task, path)
            elif action == "use_cloud":
                await runner.run_conflict_download(task, path, conflict.cloud_token)
            else:
                raise ConflictResolutionError(f"不支持的冲突解决动作: {action}")
        except ConflictResolutionError:
            raise
        except Exception as exc:
            raise ConflictResolutionError(str(exc)) from exc
        return await self._conflict_service.resolve(conflict_id, action)

    async def _resolve_task_for_conflict(
        self, conflict: ConflictItem
    ) -> SyncTaskItem | None:
        link = await self._link_service.get_by_local_path(conflict.local_path)
        if link:
            task = await self._task_service.get_task(link.task_id)
            if task:
                return task
        local_path = Path(conflict.local_path)
        try:
            target = local_path.resolve(strict=False)
        except Exception:
            target = local_path
        tasks = await self._task_service.list_tasks()
        matched: list[tuple[int, SyncTaskItem]] = []
        for task in tasks:
            root = Path(task.local_path)
            try:
                root = root.resolve(strict=False)
            except Exception:
                pass
            if self._path_within(target, root):
                matched.append((len(str(root)), task))
        if not matched:
            return None
        matched.sort(key=lambda item: item[0], reverse=True)
        return matched[0][1]

    @staticmethod
    def _path_within(target: Path, root: Path) -> bool:
        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False


__all__ = ["ConflictResolutionError", "ConflictResolutionService"]
