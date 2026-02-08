from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def repo_root() -> Path:
    env_root = os.getenv("LARKSYNC_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if (parent / "apps").exists() and (parent / "data").exists():
            return parent
    return start.parents[4]


def bundle_root() -> Path | None:
    frozen = getattr(sys, "frozen", False)
    meipass = getattr(sys, "_MEIPASS", None)
    if frozen and meipass:
        return Path(meipass).resolve()
    return None


def _is_dev_repo(root: Path) -> bool:
    return (root / "apps").exists() and (root / "data").exists()


def _default_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.getenv("APPDATA")
        if not base:
            base = Path.home() / "AppData" / "Roaming"
        return Path(base) / "LarkSync"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LarkSync"
    base = os.getenv("XDG_DATA_HOME")
    if not base:
        base = Path.home() / ".local" / "share"
    return Path(base) / "LarkSync"


def data_dir() -> Path:
    env_dir = os.getenv("LARKSYNC_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    root = repo_root()
    if _is_dev_repo(root):
        return root / "data"
    return _default_app_data_dir()


def logs_dir() -> Path:
    return data_dir() / "logs"


__all__ = [
    "repo_root",
    "data_dir",
    "logs_dir",
    "bundle_root",
    "_default_app_data_dir",
    "_is_dev_repo",
]
