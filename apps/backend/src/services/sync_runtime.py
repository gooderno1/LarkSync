"""Ephemeral execution telemetry. No logging, persistence or sync decisions here."""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Literal

RuntimePhase = Literal[
    "preparing", "scanning_cloud", "scanning_local", "checking",
    "downloading", "uploading", "deleting", "processing", "finalizing", "finished",
]
RuntimeDirection = Literal["upload", "download"]
WaitReason = Literal["local_rate_limit", "rate_limit", "retry", "remote_export", "remote_import"]


@dataclass(frozen=True)
class RuntimeWait:
    reason: WaitReason
    since: float
    resume_at: float | None = None
    attempt: int | None = None


@dataclass(frozen=True)
class SyncRuntimeSnapshot:
    schema_version: int
    execution_id: str
    active: bool
    phase: RuntimePhase
    direction: RuntimeDirection | None
    pass_kind: Literal["regular", "reconcile"]
    segment_id: int
    processed: int
    total: int | None
    discovered: int
    processed_total: int
    current_item: str | None
    operation: str | None
    started_at: float
    sampled_at: float
    elapsed_seconds: float
    activity_at: float
    progress_at: float
    wait: RuntimeWait | None


class SyncRuntime:
    def __init__(self) -> None:
        self.execution_id = str(uuid.uuid4())
        self.active = True
        self.phase: RuntimePhase = "preparing"
        self.direction: RuntimeDirection | None = None
        self.pass_kind: Literal["regular", "reconcile"] = "regular"
        self.segment_id = 0
        self.processed = 0
        self.total: int | None = None
        self.discovered = 0
        self.processed_total = 0
        self.current_item: str | None = None
        self.operation: str | None = None
        self.started_at = time.time()
        self.activity_at = self.started_at
        self.progress_at = self.started_at
        self.wait: RuntimeWait | None = None
        self._start_clock = time.monotonic()
        self._elapsed: float | None = None

    def touch(self, *, progress: bool = False) -> None:
        if not self.active:
            return
        self.activity_at = time.time()
        if progress:
            self.progress_at = self.activity_at

    def begin_phase(
        self, phase: RuntimePhase, *, direction: RuntimeDirection | None = None,
        total: int | None = None,
    ) -> None:
        if not self.active:
            return
        self.phase = phase
        self.direction = direction
        self.segment_id += 1
        self.total = total
        self.processed = 0
        self.discovered = 0
        self.current_item = None
        self.operation = None
        self.wait = None
        self.touch(progress=True)

    def discover(self, count: int = 1) -> None:
        if self.active and count > 0:
            self.discovered += count
            self.touch(progress=True)

    def set_current(self, item: str | None, *, operation: str | None = None) -> None:
        if not self.active:
            return
        self.current_item = item
        self.operation = operation
        self.touch(progress=True)

    def advance(self) -> None:
        """Call once AFTER a work item returns, including handled skips/failures."""
        if not self.active:
            return
        self.processed += 1
        self.processed_total += 1
        self.current_item = None
        self.operation = None
        self.touch(progress=True)

    def finish(self) -> None:
        if not self.active:
            return
        self._elapsed = max(0.0, time.monotonic() - self._start_clock)
        self.touch(progress=True)
        self.active = False
        self.phase = "finished"
        self.current_item = None
        self.operation = None
        self.wait = None

    def snapshot(self) -> SyncRuntimeSnapshot:
        return SyncRuntimeSnapshot(
            schema_version=1, execution_id=self.execution_id, active=self.active,
            phase=self.phase, direction=self.direction, pass_kind=self.pass_kind,
            segment_id=self.segment_id, processed=self.processed, total=self.total,
            discovered=self.discovered, processed_total=self.processed_total,
            current_item=self.current_item, operation=self.operation,
            started_at=self.started_at, sampled_at=time.time(),
            elapsed_seconds=self._elapsed if self._elapsed is not None else max(0.0, time.monotonic() - self._start_clock),
            activity_at=self.activity_at, progress_at=self.progress_at, wait=self.wait,
        )


_runtime: ContextVar[SyncRuntime | None] = ContextVar("sync_runtime", default=None)


def current_runtime() -> SyncRuntime | None:
    runtime = _runtime.get()
    return runtime if runtime is not None and runtime.active else None


@contextmanager
def runtime_scope(runtime: SyncRuntime | None) -> Iterator[None]:
    token = _runtime.set(runtime)
    try:
        yield
    finally:
        _runtime.reset(token)


@contextmanager
def runtime_wait(
    reason: WaitReason, *, delay: float | None = None, attempt: int | None = None,
) -> Iterator[None]:
    runtime = current_runtime()
    previous = runtime.wait if runtime else None
    since = time.time()
    wait = RuntimeWait(reason, since, since + max(0.0, delay) if delay is not None else None, attempt)
    if runtime:
        runtime.wait = wait
        runtime.touch()
    try:
        yield
    finally:
        if runtime and runtime.active and runtime.wait is wait:
            runtime.wait = previous
            runtime.touch()


@contextmanager
def runtime_operation(operation: str) -> Iterator[None]:
    runtime = current_runtime()
    previous = runtime.operation if runtime else None
    if runtime:
        runtime.operation = operation
        runtime.touch(progress=True)
    try:
        yield
    finally:
        if runtime and runtime.active:
            runtime.operation = previous


def begin_phase(phase: RuntimePhase, *, direction: RuntimeDirection | None = None, total: int | None = None) -> None:
    if runtime := current_runtime():
        runtime.begin_phase(phase, direction=direction, total=total)


def observe_item(item: str | None) -> None:
    if runtime := current_runtime():
        runtime.set_current(item)


def advance_item() -> None:
    if runtime := current_runtime():
        runtime.advance()


@contextmanager
def runtime_item(item: str) -> Iterator[None]:
    runtime = current_runtime()
    if runtime:
        runtime.set_current(item)
    try:
        yield
    except BaseException:
        if runtime and runtime.active:
            runtime.current_item = None
        raise
    else:
        if runtime:
            runtime.advance()


def observe_activity() -> None:
    if runtime := current_runtime():
        runtime.touch()


def discover_items(count: int = 1, *, phase: RuntimePhase) -> None:
    if (runtime := current_runtime()) and runtime.phase == phase:
        runtime.discover(count)
