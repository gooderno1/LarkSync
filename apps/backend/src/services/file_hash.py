from __future__ import annotations

import hashlib
from pathlib import Path


def calculate_file_hash(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    file_path = Path(path)
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
