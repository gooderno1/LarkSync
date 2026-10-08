from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.core.config import ConfigManager
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_path_mode import PathSyncRule, effective_sync_mode
from src.services.sync_path_policy import should_ignore_sync_path
from src.services.sync_task_service import SyncTaskItem


class SyncTaskBrowseEntry(BaseModel):
    path: str
    kind: Literal["file", "folder"]
    sync_mode: str


class SyncTaskBrowseResponse(BaseModel):
    path: str
    items: list[SyncTaskBrowseEntry]
    total: int


def browse_task_entries(
    task: SyncTaskItem, links: list[SyncLinkItem], *, path: str, search: str, offset: int, limit: int,
) -> SyncTaskBrowseResponse:
    relative = PathSyncRule(path=path, kind="folder", sync_mode="bidirectional").path if path else ""
    root = Path(task.local_path).expanduser().resolve(strict=False)
    directory = root / relative
    if not directory.resolve(strict=False).is_relative_to(root):
        raise ValueError("只能浏览当前任务根目录内的对象")
    if directory.exists() and not directory.is_dir():
        raise ValueError("请选择文件夹进行浏览")
    config = ConfigManager.get().config
    entries: dict[str, SyncTaskBrowseEntry] = {}

    def add(candidate: Path, kind: Literal["file", "folder"]) -> None:
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(root) or should_ignore_sync_path(
            task_root=root, path=candidate, ignored_subpaths=task.ignored_subpaths,
            ignore_hidden_cache_paths=config.ignore_hidden_cache_paths,
        ):
            return
        if search.casefold() not in candidate.name.casefold():
            return
        entry = SyncTaskBrowseEntry(path=candidate.relative_to(root).as_posix(), kind=kind,
                                    sync_mode=effective_sync_mode(task, candidate))
        entries[entry.path] = entry

    for link in links:
        if link.task_id != task.id:
            continue
        candidate = Path(link.local_path)
        try:
            remaining = candidate.relative_to(directory)
        except ValueError:
            continue
        if not remaining.parts:
            continue
        kind = "folder" if len(remaining.parts) > 1 or link.cloud_type == "folder" else "file"
        add(directory / remaining.parts[0], kind)
    if directory.exists():
        for candidate in directory.iterdir():
            add(candidate, "folder" if candidate.is_dir() else "file")
    items = sorted(entries.values(), key=lambda item: (item.kind != "folder", item.path.casefold()))
    return SyncTaskBrowseResponse(path=relative, items=items[offset:offset + limit], total=len(items))
