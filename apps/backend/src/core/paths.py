from __future__ import annotations

import os
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


def data_dir() -> Path:
    return repo_root() / "data"


def logs_dir() -> Path:
    return data_dir() / "logs"


__all__ = ["repo_root", "data_dir", "logs_dir"]
