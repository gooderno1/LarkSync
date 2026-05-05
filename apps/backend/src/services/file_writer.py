from __future__ import annotations

import errno
import os
import time
from collections.abc import Callable
from pathlib import Path

_LOCK_WINERRORS = {32, 33}
_LOCK_RETRY_DELAYS = (0.2, 0.5, 1.0)


class FileWriter:
    @classmethod
    def write_markdown(cls, path: Path, content: str, mtime: float) -> None:
        cls._write(
            path,
            lambda: path.write_text(content, encoding="utf-8"),
            mtime,
        )

    @classmethod
    def write_bytes(cls, path: Path, payload: bytes, mtime: float) -> None:
        cls._write(path, lambda: path.write_bytes(payload), mtime)

    @classmethod
    def _write(cls, path: Path, writer: Callable[[], object], mtime: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        cls._run_with_retry(path, writer)
        cls._run_with_retry(path, lambda: os.utime(path, (mtime, mtime)))

    @classmethod
    def _run_with_retry(cls, path: Path, action: Callable[[], object]) -> None:
        last_error: PermissionError | None = None
        for delay in (0.0, *_LOCK_RETRY_DELAYS):
            if delay > 0:
                time.sleep(delay)
            try:
                action()
                return
            except PermissionError as exc:
                if not cls._is_file_locked_error(exc):
                    raise cls._wrap_permission_error(exc, path) from exc
                last_error = exc

        if last_error is not None:
            raise cls._wrap_permission_error(last_error, path) from last_error

    @staticmethod
    def _is_file_locked_error(exc: PermissionError) -> bool:
        return getattr(exc, "winerror", None) in _LOCK_WINERRORS

    @staticmethod
    def _wrap_permission_error(
        exc: PermissionError,
        path: Path,
    ) -> PermissionError:
        winerror = getattr(exc, "winerror", None)
        if winerror in _LOCK_WINERRORS:
            return PermissionError(
                errno.EACCES,
                "目标文件正被其他程序占用，请关闭后重试",
                str(path),
            )
        return PermissionError(
            errno.EACCES,
            "没有权限写入目标文件，请检查目录权限或文件占用情况",
            str(path),
        )
