from __future__ import annotations

import threading
import time
from multiprocessing.synchronize import Event as ProcessEvent
from pathlib import Path

from src.core.process_lock import InterProcessFileLock


def _hold_lock_in_process(
    path: str,
    acquired: ProcessEvent,
    release: ProcessEvent,
) -> None:
    lock = InterProcessFileLock(Path(path), timeout_seconds=2.0)
    lock.acquire()
    acquired.set()
    release.wait(timeout=2.0)
    lock.release()


def test_interprocess_file_lock_serializes_independent_instances(tmp_path) -> None:
    lock_path = tmp_path / "oauth-refresh.lock"
    first = InterProcessFileLock(lock_path, timeout_seconds=1.0)
    second = InterProcessFileLock(lock_path, timeout_seconds=1.0)
    first_acquired = threading.Event()
    release_first = threading.Event()
    second_acquired_at: list[float] = []

    def hold_first() -> None:
        first.acquire()
        first_acquired.set()
        release_first.wait(timeout=1.0)
        first.release()

    def wait_for_second() -> None:
        first_acquired.wait(timeout=1.0)
        second.acquire()
        second_acquired_at.append(time.monotonic())
        second.release()

    first_thread = threading.Thread(target=hold_first)
    second_thread = threading.Thread(target=wait_for_second)
    first_thread.start()
    second_thread.start()
    assert first_acquired.wait(timeout=1.0)

    time.sleep(0.05)
    assert second_acquired_at == []
    released_at = time.monotonic()
    release_first.set()
    first_thread.join(timeout=1.0)
    second_thread.join(timeout=1.0)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert second_acquired_at and second_acquired_at[0] >= released_at


def test_interprocess_file_lock_times_out_without_stealing_lock(tmp_path) -> None:
    lock_path = tmp_path / "oauth-refresh.lock"
    owner = InterProcessFileLock(lock_path, timeout_seconds=1.0)
    contender = InterProcessFileLock(
        lock_path,
        timeout_seconds=0.05,
        poll_interval_seconds=0.01,
    )
    owner.acquire()
    try:
        try:
            contender.acquire()
        except TimeoutError as exc:
            assert "oauth-refresh.lock" in str(exc)
        else:
            raise AssertionError("contender unexpectedly acquired an owned lock")
    finally:
        owner.release()


def test_interprocess_file_lock_serializes_spawned_processes(tmp_path) -> None:
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "oauth-refresh-process.lock"
    first_acquired = context.Event()
    release_first = context.Event()
    second_acquired = context.Event()
    release_second = context.Event()
    first = context.Process(
        target=_hold_lock_in_process,
        args=(str(lock_path), first_acquired, release_first),
    )
    second = context.Process(
        target=_hold_lock_in_process,
        args=(str(lock_path), second_acquired, release_second),
    )

    first.start()
    assert first_acquired.wait(timeout=2.0)
    second.start()
    assert not second_acquired.wait(timeout=0.1)

    release_first.set()
    assert second_acquired.wait(timeout=2.0)
    release_second.set()
    first.join(timeout=2.0)
    second.join(timeout=2.0)

    assert first.exitcode == 0
    assert second.exitcode == 0
