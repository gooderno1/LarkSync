from __future__ import annotations

import os
from pathlib import Path


class FileWriter:
    @staticmethod
    def write_markdown(path: Path, content: str, mtime: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        os.utime(path, (mtime, mtime))

    @staticmethod
    def write_bytes(path: Path, payload: bytes, mtime: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        os.utime(path, (mtime, mtime))
