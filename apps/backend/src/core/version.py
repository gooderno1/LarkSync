from __future__ import annotations

import os
import re
from pathlib import Path

from src.core.paths import bundle_root, repo_root

_VERSION_PATTERN = re.compile(r'^version\\s*=\\s*"([^"]+)"', re.MULTILINE)


def _read_version_from(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _VERSION_PATTERN.search(content)
    if not match:
        return None
    return match.group(1)


def get_version() -> str:
    env_version = os.getenv("LARKSYNC_VERSION")
    if env_version:
        return env_version

    bundle = bundle_root()
    if bundle:
        bundled = _read_version_from(bundle / "apps" / "backend" / "pyproject.toml")
        if bundled:
            return bundled
        bundled = _read_version_from(bundle / "pyproject.toml")
        if bundled:
            return bundled

    repo = repo_root()
    repo_version = _read_version_from(repo / "apps" / "backend" / "pyproject.toml")
    if repo_version:
        return repo_version

    return "0.0.0"


__all__ = ["get_version"]
