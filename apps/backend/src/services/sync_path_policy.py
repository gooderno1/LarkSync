from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

_LOCAL_TEMP_FILE_PREFIXES = ("~$",)
_LOCAL_TEMP_FILE_SUFFIXES = (
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".part",
    ".crdownload",
    ".download",
)
_LOCAL_TEMP_FILE_NAMES = {
    ".ds_store",
    "desktop.ini",
    "thumbs.db",
}


def is_temporary_local_name(name: str) -> bool:
    lowered = (name or "").strip().lower()
    if not lowered:
        return False
    if lowered in _LOCAL_TEMP_FILE_NAMES:
        return True
    if lowered.startswith(_LOCAL_TEMP_FILE_PREFIXES):
        return True
    if lowered.startswith(".~lock.") and lowered.endswith("#"):
        return True
    return lowered.endswith(_LOCAL_TEMP_FILE_SUFFIXES)


def is_hidden_or_cache_relative_path(relative: Path) -> bool:
    for part in relative.parts:
        cleaned = part.strip()
        if not cleaned or cleaned == ".":
            continue
        if cleaned.startswith(".") or cleaned.lower() == "__pycache__":
            return True
    return False


def should_ignore_sync_path(
    *,
    task_root: str | Path,
    path: Path,
    ignored_subpaths: Iterable[str] = (),
    ignore_hidden_cache_paths: bool,
    local_trash_dir_name: str = ".larksync_trash",
    cloud_md_mirror_folder_name: str = "_LarkSync_MD_Mirror",
) -> bool:
    try:
        relative = path.relative_to(Path(task_root))
    except ValueError:
        return True
    if is_temporary_local_name(relative.name):
        return True
    lowered = {part.lower() for part in relative.parts}
    if (
        "assets" in lowered
        or "attachments" in lowered
        or "figures" in lowered
        or "插图" in relative.parts
        or local_trash_dir_name.lower() in lowered
        or cloud_md_mirror_folder_name.lower() in lowered
    ):
        return True
    if ignore_hidden_cache_paths and is_hidden_or_cache_relative_path(relative):
        return True
    relative_parts = tuple(part.lower() for part in relative.parts if part and part != ".")
    for ignored in ignored_subpaths:
        ignored_parts = tuple(
            part.lower()
            for part in Path(str(ignored).replace("\\", "/")).parts
            if part and part != "."
        )
        if ignored_parts and relative_parts[: len(ignored_parts)] == ignored_parts:
            return True
    return False


__all__ = [
    "is_hidden_or_cache_relative_path",
    "is_temporary_local_name",
    "should_ignore_sync_path",
]
