"""Resolve per-object sync directions without changing task or account ownership."""
from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from src.services.sync_task_service import SyncTaskItem

SyncDirection = Literal["upload", "download"]


def _key(path: str) -> str:
    return os.path.normcase(path).replace("\\", "/")


class PathSyncRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    kind: Literal["file", "folder"]
    sync_mode: Literal["bidirectional", "download_only", "upload_only"]

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if cleaned.startswith("/") or PureWindowsPath(cleaned).drive:
            raise ValueError("规则路径必须是任务内相对路径")
        parts = [part for part in cleaned.split("/") if part and part != "."]
        if not parts or any(part == ".." for part in parts):
            raise ValueError("规则路径不能为空或包含父目录跳转")
        if any(char in cleaned for char in ("\x00", "*", "?", ":")):
            raise ValueError("规则必须指向固定文档或文件夹，不能包含通配符或冒号")
        return "/".join(parts)


def normalize_path_rules(root: str, rules: list[PathSyncRule | dict]) -> list[PathSyncRule]:
    base = Path(root).expanduser().resolve(strict=False)
    result: list[PathSyncRule] = []
    seen: set[str] = set()
    for raw in rules:
        rule = PathSyncRule.model_validate(raw)
        key = _key(rule.path)
        if key in seen:
            raise ValueError(f"同一对象只能设置一条同步规则：{rule.path}")
        target = base / rule.path
        if not target.resolve(strict=False).is_relative_to(base):
            raise ValueError("规则目标必须位于本地同步目录内")
        if target.exists() and (target.is_dir() != (rule.kind == "folder")):
            raise ValueError(f"规则对象类型与本地目标不符：{rule.path}")
        result.append(rule)
        seen.add(key)
    return result


def _relative_key(task: SyncTaskItem, path: Path) -> str | None:
    base = Path(task.local_path).expanduser().resolve(strict=False)
    target = path.expanduser().resolve(strict=False)
    try:
        return _key(target.relative_to(base).as_posix())
    except ValueError:
        return None


def mode_supports_direction(mode: str, direction: SyncDirection) -> bool:
    return mode in {"bidirectional", f"{direction}_only"}


def task_supports_direction(task: SyncTaskItem, direction: SyncDirection) -> bool:
    return mode_supports_direction(task.sync_mode, direction) or any(
        mode_supports_direction(rule.sync_mode, direction) for rule in task.path_sync_rules
    )


def effective_sync_mode(task: SyncTaskItem, path: Path) -> str:
    relative = _relative_key(task, path)
    best: tuple[int, int] = (-1, -1)
    mode = task.sync_mode
    for rule in task.path_sync_rules:
        key = _key(rule.path)
        matches = relative == key or (
            rule.kind == "folder" and relative is not None and relative.startswith(f"{key}/")
        )
        rank = (len(key.split("/")), int(rule.kind == "file"))
        if matches and rank > best:
            mode, best = rule.sync_mode, rank
    return mode


def path_supports_direction(task: SyncTaskItem, path: Path, direction: SyncDirection) -> bool:
    return _relative_key(task, path) is not None and mode_supports_direction(
        effective_sync_mode(task, path), direction,
    )


def task_for_path(task: SyncTaskItem, path: Path) -> SyncTaskItem:
    mode = effective_sync_mode(task, path)
    md_mode = task.md_sync_mode
    if task.sync_mode == "download_only" and mode_supports_direction(mode, "upload") and md_mode == "download_only":
        md_mode = "doc_only"
    if task.sync_mode == mode and task.md_sync_mode == md_mode:
        return task
    return replace(task, sync_mode=mode, md_sync_mode=md_mode)


def can_delete_path(
    task: SyncTaskItem, path: Path, direction: SyncDirection, *, is_directory: bool = False,
) -> bool:
    if not path_supports_direction(task, path, direction):
        return False
    relative = _relative_key(task, path)
    if relative is None:
        return False
    for ignored in task.ignored_subpaths:
        key = _key(ignored.replace("\\", "/").strip("/"))
        if relative == key or relative.startswith(f"{key}/"):
            return False
        if is_directory and key.startswith(f"{relative}/"):
            return False
    if is_directory:
        for rule in task.path_sync_rules:
            key = _key(rule.path)
            if key.startswith(f"{relative}/") and not mode_supports_direction(rule.sync_mode, direction):
                return False
    return True
