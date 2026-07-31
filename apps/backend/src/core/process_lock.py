from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import BinaryIO


class InterProcessFileLock:
    """基于操作系统文件锁的跨进程互斥锁。"""

    def __init__(
        self,
        path: Path,
        *,
        timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        self.path = path.expanduser().resolve()
        self.timeout_seconds = max(0.0, timeout_seconds)
        self.poll_interval_seconds = max(0.005, poll_interval_seconds)
        self._handle: BinaryIO | None = None
        self._acquired = False

    def acquire(self) -> None:
        if self._acquired:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            self._ensure_lock_byte(handle)
            deadline = time.monotonic() + self.timeout_seconds
            while True:
                if self._try_lock(handle):
                    self._handle = handle
                    self._acquired = True
                    return
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"等待跨进程锁超时: {self.path}")
                time.sleep(self.poll_interval_seconds)
        except BaseException:
            handle.close()
            raise

    def release(self) -> None:
        handle = self._handle
        if not self._acquired or handle is None:
            return
        self._handle = None
        self._acquired = False
        try:
            self._unlock(handle)
        finally:
            handle.close()

    @staticmethod
    def _ensure_lock_byte(handle: BinaryIO) -> None:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)

    @staticmethod
    def _try_lock(handle: BinaryIO) -> bool:
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return False
            return True

        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    @staticmethod
    def _unlock(handle: BinaryIO) -> None:
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["InterProcessFileLock"]
