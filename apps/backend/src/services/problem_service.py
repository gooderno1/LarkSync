from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import (
    ConflictRecord,
    ProblemActionRecord,
    ProblemOccurrence,
    ProblemRecoveryFact,
    ProblemRecord,
    SyncMeta,
    SyncRun,
    SyncRunEvent,
    SyncTask,
    SyncTaskCheckState,
)
from src.core.config import ConfigManager
from src.db.session import get_session_maker
from src.services.sync_path_policy import should_ignore_sync_path


CLASSIFIER_VERSION = "problem-classifier-v3"
PROBLEM_STATUSES = {
    "failed",
    "delete_failed",
    "cancelled",
}
RECOVERY_STATUSES = {
    "uploaded",
    "downloaded",
    "deleted",
    "created",
    "linked",
    "mirrored",
}
LEGACY_PROBLEM_EVENT_CURSOR_KEY = "problem_event_cursor_v3"
PROBLEM_HISTORY_CURSOR_KEY = "problem_history_cursor_v3"
PROBLEM_EVENT_CURSOR_KEY = "problem_event_cursor_v4"
PROBLEM_OCCURRENCE_RECOUNT_KEY = "problem_occurrence_recount_v1"
_REQUEST_ID_PATTERN = re.compile(
    r"(?i)(?:request[_ -]?id|x-tt-logid|trace[_ -]?id)\s*[:=]\s*[^\s,;]+"
)
_TOKEN_PATTERN = re.compile(
    r"(?i)(?:access_token|refresh_token|app_secret|authorization)\s*[:=]\s*[^\s,;]+"
)
_RUN_SUMMARY_PATTERN = re.compile(
    r"^完成:\s*total=(\d+)\s+ok=(\d+)\s+failed=(\d+)\s+skipped=(\d+)\s*$"
)


@dataclass(frozen=True)
class AvailableProblemAction:
    key: str
    label: str
    tone: str = "neutral"
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ProblemItem:
    id: str
    fingerprint: str
    category: str
    severity: str
    state: str
    title: str
    summary: str
    task_id: str | None
    object_kind: str
    object_key: str
    object_path: str | None
    first_seen_at: float
    last_seen_at: float
    occurrence_count: int
    latest_run_id: str | None
    latest_event_id: str | None
    classifier_version: str
    resolution_verification: str | None
    resolved_at: float | None
    ignored_reason: str | None
    ignored_at: float | None
    resolution_key: str | None
    operation_family: str | None
    actionability: str
    resolved_by_run_id: str | None
    resolved_by_event_id: str | None
    last_good_at: float | None
    available_actions: tuple[AvailableProblemAction, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProblemOccurrenceItem:
    id: str
    problem_id: str
    source_kind: str
    source_id: str
    run_id: str | None
    event_id: str | None
    occurred_at: float
    evidence_json: str


@dataclass(frozen=True)
class ProblemActionItem:
    id: str
    problem_id: str
    action_key: str
    requested_at: float
    started_at: float | None
    finished_at: float | None
    result: str
    error_code: str | None
    error_message: str | None
    verification_result: str | None


@dataclass(frozen=True)
class ProblemRefreshResult:
    events_seen: int
    conflicts_seen: int


@dataclass(frozen=True)
class ProblemReconcileResult:
    scanned: int
    resolved: int


@dataclass(frozen=True)
class _Classification:
    category: str
    severity: str
    title: str
    summary: str
    normalized_error_code: str


class ProblemService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        ignore_hidden_cache_paths: bool | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._refresh_lock = asyncio.Lock()
        self._reconcile_cursor: tuple[float, str] | None = None
        self._ignore_hidden_cache_paths = ignore_hidden_cache_paths

    async def refresh_sources(self, *, event_limit: int | None = 1000) -> ProblemRefreshResult:
        async with self._refresh_lock:
            return await self._refresh_sources(event_limit=event_limit)

    async def initialize_live_cursor(self) -> bool:
        """建立实时消费基线；保留旧历史位置，但不在启动阶段继续重放。"""
        async with self._refresh_lock:
            async with self._session_maker() as session:
                existing = await session.get(SyncMeta, PROBLEM_EVENT_CURSOR_KEY)
                if existing is not None:
                    return False
                legacy = await session.get(SyncMeta, LEGACY_PROBLEM_EVENT_CURSOR_KEY)
                history = await session.get(SyncMeta, PROBLEM_HISTORY_CURSOR_KEY)
                if legacy is not None and history is None:
                    session.add(
                        SyncMeta(
                            key=PROBLEM_HISTORY_CURSOR_KEY,
                            value=legacy.value,
                            updated_at=time.time(),
                        )
                    )
                latest_row = await session.execute(
                    select(SyncRunEvent.timestamp, SyncRunEvent.id)
                    .order_by(SyncRunEvent.timestamp.desc(), SyncRunEvent.id.desc())
                    .limit(1)
                )
                latest = latest_row.one_or_none()
                await self._store_event_cursor(
                    session,
                    timestamp=float(latest.timestamp) if latest else 0.0,
                    event_id=str(latest.id) if latest else "",
                )
                await session.commit()
                return True

    async def backfill_sources(self, *, batch_size: int = 1000) -> ProblemRefreshResult:
        events_seen = 0
        conflicts_seen = 0
        while True:
            result = await self.refresh_sources(event_limit=batch_size)
            events_seen += result.events_seen
            conflicts_seen = max(conflicts_seen, result.conflicts_seen)
            if result.events_seen < batch_size:
                break
            await asyncio.sleep(0)
        return ProblemRefreshResult(events_seen=events_seen, conflicts_seen=conflicts_seen)

    async def reconcile_current_state(
        self,
        *,
        batch_size: int = 500,
        max_batches: int = 10,
    ) -> ProblemReconcileResult:
        safe_batch_size = max(1, int(batch_size or 1))
        safe_max_batches = max(1, int(max_batches or 1))
        scanned = 0
        resolved = 0
        async with self._refresh_lock:
            for _ in range(safe_max_batches):
                async with self._session_maker() as session:
                    stmt = (
                        select(ProblemRecord)
                        .where(ProblemRecord.state.in_(["open", "in_progress", "waiting"]))
                        .order_by(ProblemRecord.last_seen_at.asc(), ProblemRecord.id.asc())
                        .limit(safe_batch_size)
                    )
                    if self._reconcile_cursor is not None:
                        cursor_time, cursor_id = self._reconcile_cursor
                        stmt = stmt.where(
                            or_(
                                ProblemRecord.last_seen_at > cursor_time,
                                (
                                    (ProblemRecord.last_seen_at == cursor_time)
                                    & (ProblemRecord.id > cursor_id)
                                ),
                            )
                        )
                    rows = list((await session.execute(stmt)).scalars().all())
                    if not rows:
                        self._reconcile_cursor = None
                        break
                    last = rows[-1]
                    self._reconcile_cursor = (last.last_seen_at, last.id)
                    scanned += len(rows)

                    task_ids = {item.task_id for item in rows if item.task_id}
                    tasks: dict[str, SyncTask] = {}
                    if task_ids:
                        task_rows = await session.execute(
                            select(SyncTask).where(SyncTask.id.in_(task_ids))
                        )
                        tasks = {item.id: item for item in task_rows.scalars().all()}
                    latest_success: dict[tuple[str, str], tuple[str, float]] = {}
                    latest_successful_check: dict[tuple[str, str], float] = {}
                    if task_ids:
                        min_seen_at = min(item.last_seen_at for item in rows)
                        run_rows = await session.execute(
                            select(
                                SyncRun.task_id,
                                SyncRun.run_id,
                                SyncRun.finished_at,
                                SyncRun.trigger_source,
                            )
                            .where(SyncRun.task_id.in_(task_ids))
                            .where(SyncRun.state == "success")
                            .where(SyncRun.finished_at.is_not(None))
                            .where(SyncRun.finished_at > min_seen_at)
                            .order_by(SyncRun.finished_at.desc())
                        )
                        for task_id, run_id, finished_at, trigger_source in run_rows.all():
                            task_key = str(task_id)
                            value = (str(run_id), float(finished_at))
                            latest_success.setdefault((task_key, "any"), value)
                            direction = self.operation_hint_from_trigger(trigger_source)
                            if direction in {"upload", "download"}:
                                latest_success.setdefault((task_key, direction), value)
                        check_rows = await session.execute(
                            select(
                                SyncTaskCheckState.task_id,
                                SyncTaskCheckState.direction,
                                SyncTaskCheckState.finished_at,
                            )
                            .where(SyncTaskCheckState.task_id.in_(task_ids))
                            .where(
                                SyncTaskCheckState.state.in_(["no_change", "changes_found"])
                            )
                            .where(SyncTaskCheckState.last_error.is_(None))
                            .where(SyncTaskCheckState.finished_at.is_not(None))
                            .where(SyncTaskCheckState.finished_at > min_seen_at)
                            .order_by(SyncTaskCheckState.finished_at.desc())
                        )
                        for task_id, direction, finished_at in check_rows.all():
                            normalized_direction = str(direction or "").lower()
                            if normalized_direction in {"upload", "download"}:
                                latest_successful_check.setdefault(
                                    (str(task_id), normalized_direction),
                                    float(finished_at),
                                )

                    ignore_hidden_cache_paths = self._ignore_hidden_cache_paths
                    if ignore_hidden_cache_paths is None:
                        ignore_hidden_cache_paths = (
                            ConfigManager.get().config.ignore_hidden_cache_paths
                        )
                    decisions = await asyncio.to_thread(
                        self._build_current_state_decisions,
                        rows,
                        tasks,
                        latest_success,
                        latest_successful_check,
                        ignore_hidden_cache_paths,
                    )
                    now = time.time()
                    for problem, verification, evidence_at, run_id in decisions:
                        problem.state = "resolved"
                        problem.resolved_at = evidence_at or now
                        problem.last_good_at = evidence_at or now
                        problem.resolution_verification = verification
                        if run_id:
                            problem.resolved_by_run_id = run_id
                        resolved += 1
                    await session.commit()
                if len(rows) < safe_batch_size:
                    self._reconcile_cursor = None
                    break
                await asyncio.sleep(0)
        return ProblemReconcileResult(scanned=scanned, resolved=resolved)

    @staticmethod
    def _build_current_state_decisions(
        problems: list[ProblemRecord],
        tasks: dict[str, SyncTask],
        latest_success: dict[tuple[str, str], tuple[str, float]],
        latest_successful_check: dict[tuple[str, str], float],
        ignore_hidden_cache_paths: bool,
    ) -> list[tuple[ProblemRecord, str, float | None, str | None]]:
        decisions: list[tuple[ProblemRecord, str, float | None, str | None]] = []
        for problem in problems:
            task_id = problem.task_id or ""
            task = tasks.get(task_id)
            if task_id and (task is None or not task.enabled):
                decisions.append((problem, "task_inactive", None, None))
                continue
            if task is None:
                continue
            successful_run = latest_success.get((task_id, "any"))
            if (
                successful_run
                and successful_run[1] > problem.last_seen_at
                and problem.operation_family == "task_auth"
            ):
                decisions.append(
                    (
                        problem,
                        "task_auth_recovered",
                        successful_run[1],
                        successful_run[0],
                    )
                )
                continue
            if problem.object_kind == "task_run":
                direction = problem.operation_family or "any"
                directional_run = latest_success.get((task_id, direction))
                directional_check = latest_successful_check.get((task_id, direction))
                if direction not in {"upload", "download"}:
                    directional_run = successful_run
                if directional_run and directional_run[1] > problem.last_seen_at:
                    verification = (
                        "later_matching_run_succeeded"
                        if direction in {"upload", "download"}
                        else "later_run_succeeded"
                    )
                    decisions.append(
                        (
                            problem,
                            verification,
                            directional_run[1],
                            directional_run[0],
                        )
                    )
                elif (
                    direction in {"upload", "download"}
                    and directional_check is not None
                    and directional_check > problem.last_seen_at
                ):
                    decisions.append(
                        (
                            problem,
                            "later_matching_check_succeeded",
                            directional_check,
                            None,
                        )
                    )
                continue
            if (
                successful_run
                and successful_run[1] > problem.last_seen_at
                and (
                    problem.operation_family == "task_run"
                    or problem.category == "system"
                )
            ):
                decisions.append(
                    (
                        problem,
                        "later_run_succeeded",
                        successful_run[1],
                        successful_run[0],
                    )
                )
                continue
            if problem.operation_family == "task_auth":
                continue
            object_path = (problem.object_path or problem.object_key or "").replace(
                "\\",
                "/",
            )
            if not object_path or object_path == "未知对象":
                continue
            object_candidate = Path(object_path)
            path = (
                object_candidate
                if object_candidate.is_absolute()
                else Path(task.local_path).joinpath(
                    *(part for part in object_path.split("/") if part)
                )
            )
            ignored_subpaths = ProblemService._parse_ignored_subpaths(
                task.ignored_subpaths
            )
            if should_ignore_sync_path(
                task_root=task.local_path,
                path=path,
                ignored_subpaths=ignored_subpaths,
                ignore_hidden_cache_paths=ignore_hidden_cache_paths,
            ):
                decisions.append((problem, "path_excluded", None, None))
                continue
            if (
                problem.operation_family in {"upload", "conversion", "delete"}
                or problem.category == "local_io"
            ):
                try:
                    task_root_available = Path(task.local_path).is_dir()
                except OSError:
                    task_root_available = False
                if not task_root_available:
                    continue
                try:
                    exists = path.exists()
                except OSError:
                    exists = True
                if not exists:
                    decisions.append(
                        (problem, "target_absent_verified", None, None)
                    )
        return decisions

    @staticmethod
    def _parse_ignored_subpaths(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if str(item).strip()]

    async def _refresh_sources(self, *, event_limit: int | None) -> ProblemRefreshResult:
        async with self._session_maker() as session:
            task_rows = await session.execute(select(SyncTask.id, SyncTask.local_path))
            task_roots = {str(task_id): str(root) for task_id, root in task_rows.all()}
            await self._migrate_active_event_problems(session, task_roots=task_roots)
            await self._recount_legacy_occurrences(session)
            cursor_timestamp, cursor_event_id = await self._load_event_cursor(session)
            event_stmt = (
                select(SyncRunEvent)
                .where(SyncRunEvent.status.in_(PROBLEM_STATUSES | RECOVERY_STATUSES))
                .where(
                    or_(
                        SyncRunEvent.timestamp > cursor_timestamp,
                        (
                            (SyncRunEvent.timestamp == cursor_timestamp)
                            & (SyncRunEvent.id > cursor_event_id)
                        ),
                    )
                )
                .order_by(SyncRunEvent.timestamp.asc(), SyncRunEvent.id.asc())
            )
            if event_limit is not None:
                event_stmt = event_stmt.limit(max(1, event_limit))
            event_rows = await session.execute(event_stmt)
            events = list(event_rows.scalars().all())
            run_triggers = await self._load_run_triggers(
                session,
                [event.run_id for event in events],
            )
            problem_fingerprints: set[str] = set()
            for event in events:
                if event.status not in PROBLEM_STATUSES:
                    continue
                if self.is_failed_run_summary(event.status, event.message):
                    continue
                _, object_key = self.normalize_object_path(
                    event.path,
                    task_roots.get(event.task_id),
                )
                classification = self.classify_event(
                    event.status,
                    event.path,
                    event.message,
                    operation_hint=self.operation_hint_from_trigger(
                        run_triggers.get(event.run_id or "")
                    ),
                )
                problem_fingerprints.add(
                    self.build_fingerprint(
                        source_kind="sync_event",
                        task_id=event.task_id,
                        category=classification.category,
                        stage=event.status,
                        normalized_error_code=classification.normalized_error_code,
                        object_key=object_key,
                    )
                )
            problem_records: list[ProblemRecord] = []
            if problem_fingerprints:
                problem_rows = await session.execute(
                    select(ProblemRecord).where(
                        ProblemRecord.fingerprint.in_(problem_fingerprints)
                    )
                )
                problem_records = list(problem_rows.scalars().all())
            problems_by_fingerprint = {record.fingerprint: record for record in problem_records}
            conflict_rows = await session.execute(
                select(ConflictRecord).order_by(ConflictRecord.created_at.desc()).limit(5000)
            )
            conflicts = list(conflict_rows.scalars().all())
            source_rows = await session.execute(
                select(
                    ProblemOccurrence.source_kind,
                    ProblemOccurrence.source_id,
                    ProblemOccurrence.problem_id,
                ).where(ProblemOccurrence.source_kind == "conflict")
            )
            known_conflicts: dict[str, str] = {}
            for source_kind, source_id, problem_id in source_rows.all():
                if source_kind == "conflict":
                    known_conflicts[str(source_id)] = str(problem_id)
            for event in events:
                if event.status in PROBLEM_STATUSES:
                    if self.is_failed_run_summary(event.status, event.message):
                        continue
                    await self._ingest_event(
                        session,
                        event,
                        task_root=task_roots.get(event.task_id),
                        operation_hint=self.operation_hint_from_trigger(
                            run_triggers.get(event.run_id or "")
                        ),
                        occurrence_known_absent=False,
                        problems_by_fingerprint=problems_by_fingerprint,
                    )
                else:
                    await self._ingest_recovery_event(
                        session,
                        event,
                        task_root=task_roots.get(event.task_id),
                    )
            for conflict in reversed(conflicts):
                await self._ingest_conflict(
                    session,
                    conflict,
                    task_roots=task_roots,
                    existing_problem_id=known_conflicts.get(conflict.id),
                )
            if events:
                last_event = events[-1]
                await self._store_event_cursor(
                    session,
                    timestamp=last_event.timestamp,
                    event_id=last_event.id,
                )
            await session.commit()
        return ProblemRefreshResult(events_seen=len(events), conflicts_seen=len(conflicts))

    async def _recount_legacy_occurrences(self, session: AsyncSession) -> None:
        """一次性排除历史运行汇总，修正问题中心的异常出现次数。"""

        if await session.get(SyncMeta, PROBLEM_OCCURRENCE_RECOUNT_KEY) is not None:
            return
        problem_rows = await session.execute(
            select(ProblemRecord).where(
                ProblemRecord.state.in_(["open", "in_progress", "waiting", "ignored"])
            )
        )
        problems = list(problem_rows.scalars().all())
        if problems:
            problem_ids = [problem.id for problem in problems]
            occurrence_rows = await session.execute(
                select(
                    ProblemOccurrence.problem_id,
                    ProblemOccurrence.source_kind,
                    SyncRunEvent.status,
                    SyncRunEvent.message,
                )
                .outerjoin(
                    SyncRunEvent,
                    SyncRunEvent.id == ProblemOccurrence.event_id,
                )
                .where(ProblemOccurrence.problem_id.in_(problem_ids))
            )
            counts = {problem.id: 0 for problem in problems}
            for problem_id, source_kind, status, message in occurrence_rows.all():
                if (
                    source_kind == "sync_event"
                    and self.is_failed_run_summary(status or "", message)
                ):
                    continue
                counts[str(problem_id)] += 1
            for problem in problems:
                problem.occurrence_count = max(1, counts[problem.id])
        now = time.time()
        session.add(
            SyncMeta(
                key=PROBLEM_OCCURRENCE_RECOUNT_KEY,
                value=json.dumps({"completed_at": now}, ensure_ascii=False),
                updated_at=now,
            )
        )

    async def _migrate_active_event_problems(
        self,
        session: AsyncSession,
        *,
        task_roots: dict[str, str],
        limit: int = 500,
    ) -> None:
        has_run_summary_event = (
            select(SyncRunEvent.id)
            .where(SyncRunEvent.id == ProblemRecord.latest_event_id)
            .where(SyncRunEvent.status == "failed")
            .where(SyncRunEvent.message.like("完成:%"))
            .exists()
        )
        rows = await session.execute(
            select(ProblemRecord)
            .where(ProblemRecord.object_kind.in_(["sync_event", "task_run"]))
            .where(
                or_(
                    ProblemRecord.classifier_version != CLASSIFIER_VERSION,
                    has_run_summary_event,
                )
            )
            .where(
                ProblemRecord.state.in_(
                    ["open", "in_progress", "waiting", "ignored"]
                )
            )
            .order_by(ProblemRecord.last_seen_at.desc())
            .limit(max(1, limit))
        )
        problems = list(rows.scalars().all())
        event_ids = [
            problem.latest_event_id
            for problem in problems
            if problem.latest_event_id
        ]
        if not event_ids:
            return
        event_rows = await session.execute(
            select(SyncRunEvent).where(SyncRunEvent.id.in_(event_ids))
        )
        events = {event.id: event for event in event_rows.scalars().all()}
        run_triggers = await self._load_run_triggers(
            session,
            [event.run_id for event in events.values()],
        )

        migration_targets: list[
            tuple[
                ProblemRecord,
                SyncRunEvent,
                _Classification,
                str,
                str,
                str,
                str,
            ]
        ] = []
        for problem in problems:
            event = events.get(problem.latest_event_id or "")
            if event is None:
                continue
            is_run_summary = self.is_failed_run_summary(event.status, event.message)
            if (
                problem.classifier_version == CLASSIFIER_VERSION
                and not is_run_summary
            ):
                continue
            problem.classifier_version = CLASSIFIER_VERSION
            if is_run_summary:
                problem.object_kind = "task_run"
                problem.state = "resolved"
                problem.resolved_at = event.timestamp
                problem.last_good_at = event.timestamp
                problem.resolution_verification = "workflow_summary_not_problem"
                problem.actionability = "diagnostic_only"
                problem.ignored_reason = None
                problem.ignored_at = None
                continue
            task_root = task_roots.get(event.task_id)
            object_path, object_key = self.normalize_object_path(event.path, task_root)
            operation_hint = self.operation_hint_from_trigger(
                run_triggers.get(event.run_id or "")
            )
            classification = self.classify_event(
                event.status,
                event.path,
                event.message,
                operation_hint=operation_hint,
            )
            object_kind = self.event_object_kind(event.path, task_root)
            operation_family = self.operation_family_for_problem(
                classification.category,
                event.status,
            )
            fingerprint = self.build_fingerprint(
                source_kind="sync_event",
                task_id=event.task_id,
                category=classification.category,
                stage=event.status,
                normalized_error_code=classification.normalized_error_code,
                object_key=object_key,
            )
            migration_targets.append(
                (
                    problem,
                    event,
                    classification,
                    object_path,
                    object_key,
                    object_kind,
                    fingerprint,
                )
            )
            problem.operation_family = operation_family
            problem.resolution_key = self.build_resolution_key(
                task_id=event.task_id,
                object_key=object_key,
                operation_family=operation_family,
            )

        target_fingerprints = {item[6] for item in migration_targets}
        existing_by_fingerprint: dict[str, ProblemRecord] = {}
        if target_fingerprints:
            existing_rows = await session.execute(
                select(ProblemRecord).where(
                    ProblemRecord.fingerprint.in_(target_fingerprints)
                )
            )
            existing_by_fingerprint = {
                item.fingerprint: item for item in existing_rows.scalars().all()
            }

        claimed_fingerprints = dict(existing_by_fingerprint)
        for (
            problem,
            event,
            classification,
            object_path,
            object_key,
            object_kind,
            fingerprint,
        ) in migration_targets:
            existing = claimed_fingerprints.get(fingerprint)
            if existing is not None and existing.id != problem.id:
                problem.state = "resolved"
                problem.resolved_at = event.timestamp
                problem.last_good_at = event.timestamp
                problem.resolution_verification = "superseded_by_reclassification"
                problem.actionability = "diagnostic_only"
                continue
            problem.fingerprint = fingerprint
            claimed_fingerprints[fingerprint] = problem
            problem.category = classification.category
            problem.severity = classification.severity
            problem.title = classification.title
            problem.summary = classification.summary
            problem.object_kind = object_kind
            problem.object_path = object_path
            problem.object_key = object_key
            problem.actionability = self.actionability_for_category(
                classification.category
            )
            if (
                classification.category == "upload"
                and (event.message or "").strip() == "文件大小不能为空"
            ):
                problem.state = "resolved"
                problem.resolved_at = event.timestamp
                problem.last_good_at = event.timestamp
                problem.resolution_verification = "zero_byte_file_now_skipped"
                problem.ignored_reason = None
                problem.ignored_at = None

    @staticmethod
    async def _load_run_triggers(
        session: AsyncSession,
        run_ids: Iterable[str | None],
    ) -> dict[str, str]:
        normalized = {str(run_id) for run_id in run_ids if run_id}
        if not normalized:
            return {}
        rows = await session.execute(
            select(SyncRun.run_id, SyncRun.trigger_source).where(
                SyncRun.run_id.in_(normalized)
            )
        )
        return {
            str(run_id): str(trigger_source or "")
            for run_id, trigger_source in rows.all()
        }

    @staticmethod
    def is_failed_run_summary(status: str, message: str | None) -> bool:
        if status.strip().lower() != "failed":
            return False
        match = _RUN_SUMMARY_PATTERN.fullmatch((message or "").strip())
        return match is not None

    @staticmethod
    def operation_hint_from_trigger(trigger_source: str | None) -> str | None:
        normalized = (trigger_source or "").strip().lower()
        if "upload" in normalized:
            return "upload"
        if "download" in normalized:
            return "download"
        return None

    @classmethod
    def event_object_kind(cls, path: str, task_root: str | None) -> str:
        normalized_path = (path or "").strip().replace("\\", "/").rstrip("/").casefold()
        normalized_root = (
            (task_root or "").strip().replace("\\", "/").rstrip("/").casefold()
        )
        if normalized_root and normalized_path == normalized_root:
            return "task_run"
        return "sync_object"

    @staticmethod
    async def _load_event_cursor(session: AsyncSession) -> tuple[float, str]:
        record = await session.get(SyncMeta, PROBLEM_EVENT_CURSOR_KEY)
        if not record or not record.value:
            return 0.0, ""
        try:
            payload = json.loads(record.value)
            return float(payload.get("timestamp", 0.0)), str(payload.get("event_id", ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            return 0.0, ""

    @staticmethod
    async def _store_event_cursor(
        session: AsyncSession,
        *,
        timestamp: float,
        event_id: str,
    ) -> None:
        record = await session.get(SyncMeta, PROBLEM_EVENT_CURSOR_KEY)
        value = json.dumps(
            {"timestamp": float(timestamp), "event_id": str(event_id)},
            ensure_ascii=False,
        )
        if record:
            record.value = value
            record.updated_at = time.time()
            return
        session.add(
            SyncMeta(
                key=PROBLEM_EVENT_CURSOR_KEY,
                value=value,
                updated_at=time.time(),
            )
        )

    async def list_problems(
        self,
        *,
        state: str = "",
        categories: Iterable[str] | None = None,
        severities: Iterable[str] | None = None,
        task_id: str = "",
        search: str = "",
        since: float | None = None,
        until: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[ProblemItem]]:
        filters: list[object] = []
        normalized_states = {part.strip() for part in state.split(",") if part.strip()}
        normalized_categories = {value.strip() for value in categories or [] if value.strip()}
        normalized_severities = {value.strip() for value in severities or [] if value.strip()}
        if normalized_states:
            filters.append(ProblemRecord.state.in_(normalized_states))
        if normalized_categories:
            filters.append(ProblemRecord.category.in_(normalized_categories))
        if normalized_severities:
            filters.append(ProblemRecord.severity.in_(normalized_severities))
        if task_id.strip():
            filters.append(ProblemRecord.task_id == task_id.strip())
        if search.strip():
            pattern = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(ProblemRecord.title).like(pattern),
                    func.lower(ProblemRecord.summary).like(pattern),
                    func.lower(func.coalesce(ProblemRecord.object_path, "")).like(pattern),
                    func.lower(func.coalesce(ProblemRecord.task_id, "")).like(pattern),
                )
            )
        if since is not None:
            filters.append(ProblemRecord.last_seen_at >= since)
        if until is not None:
            filters.append(ProblemRecord.last_seen_at <= until)
        count_stmt = select(func.count()).select_from(ProblemRecord)
        data_stmt = select(ProblemRecord)
        if filters:
            count_stmt = count_stmt.where(*filters)
            data_stmt = data_stmt.where(*filters)
        severity_rank = case(
            (ProblemRecord.severity == "critical", 4),
            (ProblemRecord.severity == "high", 3),
            (ProblemRecord.severity == "medium", 2),
            (ProblemRecord.severity == "low", 1),
            else_=0,
        )
        data_stmt = (
            data_stmt.order_by(severity_rank.desc(), ProblemRecord.last_seen_at.desc())
            .limit(max(1, limit))
            .offset(max(0, offset))
        )
        async with self._session_maker() as session:
            total = int((await session.execute(count_stmt)).scalar_one() or 0)
            records = list((await session.execute(data_stmt)).scalars().all())
        return total, [self._to_item(record) for record in records]

    async def get_problem(self, problem_id: str) -> ProblemItem | None:
        async with self._session_maker() as session:
            record = await session.get(ProblemRecord, problem_id)
            return self._to_item(record) if record else None

    async def get_summary(self) -> dict[str, object]:
        async with self._session_maker() as session:
            state_rows = await session.execute(
                select(ProblemRecord.state, func.count()).group_by(ProblemRecord.state)
            )
            category_rows = await session.execute(
                select(ProblemRecord.category, func.count())
                .where(ProblemRecord.state.in_(["open", "in_progress", "waiting"]))
                .group_by(ProblemRecord.category)
            )
            severity_rows = await session.execute(
                select(ProblemRecord.severity, func.count())
                .where(ProblemRecord.state.in_(["open", "in_progress", "waiting"]))
                .group_by(ProblemRecord.severity)
            )
        by_state = {str(key): int(value) for key, value in state_rows.all()}
        return {
            "total": sum(by_state.values()),
            "unresolved": sum(by_state.get(key, 0) for key in ("open", "in_progress", "waiting")),
            "by_state": by_state,
            "by_category": {str(key): int(value) for key, value in category_rows.all()},
            "by_severity": {str(key): int(value) for key, value in severity_rows.all()},
        }

    async def list_occurrences(
        self,
        problem_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProblemOccurrenceItem]:
        async with self._session_maker() as session:
            rows = await session.execute(
                select(ProblemOccurrence)
                .where(ProblemOccurrence.problem_id == problem_id)
                .order_by(ProblemOccurrence.occurred_at.desc())
                .limit(max(1, limit))
                .offset(max(0, offset))
            )
            return [self._to_occurrence(item) for item in rows.scalars().all()]

    async def list_actions(
        self,
        problem_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProblemActionItem]:
        async with self._session_maker() as session:
            rows = await session.execute(
                select(ProblemActionRecord)
                .where(ProblemActionRecord.problem_id == problem_id)
                .order_by(ProblemActionRecord.requested_at.desc())
                .limit(max(1, limit))
                .offset(max(0, offset))
            )
            return [self._to_action(item) for item in rows.scalars().all()]

    async def start_action(self, problem_id: str, action_key: str) -> ProblemActionItem:
        now = time.time()
        async with self._session_maker() as session:
            problem = await session.get(ProblemRecord, problem_id)
            if not problem:
                raise LookupError("Problem not found")
            allowed = {action.key for action in self._available_actions(problem)}
            if action_key not in allowed:
                raise ValueError("Action is not available for this problem")
            existing = await session.execute(
                select(ProblemActionRecord)
                .where(ProblemActionRecord.problem_id == problem_id)
                .where(ProblemActionRecord.action_key == action_key)
                .where(ProblemActionRecord.result.in_(["queued", "running"]))
                .limit(1)
            )
            if existing.scalar_one_or_none():
                raise ValueError("The same action is already running")
            record = ProblemActionRecord(
                id=str(uuid.uuid4()),
                problem_id=problem_id,
                action_key=action_key,
                requested_at=now,
                started_at=now,
                result="running",
            )
            problem.state = "in_progress"
            problem.resolution_verification = "action_running"
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return self._to_action(record)

    async def finish_action(
        self,
        action_id: str,
        *,
        result: str,
        error_code: str | None = None,
        error_message: str | None = None,
        verification_result: str | None = None,
    ) -> ProblemActionItem:
        async with self._session_maker() as session:
            action = await session.get(ProblemActionRecord, action_id)
            if not action:
                raise LookupError("Problem action not found")
            problem = await session.get(ProblemRecord, action.problem_id)
            if not problem:
                raise LookupError("Problem not found")
            now = time.time()
            action.finished_at = now
            action.result = result
            action.error_code = error_code
            action.error_message = self.sanitize_evidence_text(error_message)
            action.verification_result = verification_result
            ignored_without_resolution = (
                problem.state == "ignored"
                and verification_result
                not in {"verified", "source_resolved", "later_run_succeeded"}
            )
            if ignored_without_resolution:
                problem.resolution_verification = "manually_ignored"
            else:
                problem.resolution_verification = verification_result
                if result == "failed":
                    problem.state = "open"
                    problem.resolved_at = None
                elif verification_result in {"verified", "source_resolved", "later_run_succeeded"}:
                    problem.state = "resolved"
                    problem.resolved_at = now
                    problem.ignored_reason = None
                    problem.ignored_at = None
                elif verification_result and verification_result.startswith("waiting"):
                    problem.state = "waiting"
                elif action.action_key == "open_local_folder":
                    problem.state = "open"
                else:
                    problem.state = "waiting"
            await session.commit()
            await session.refresh(action)
            return self._to_action(action)

    async def ignore_problem(self, problem_id: str, reason: str) -> ProblemItem:
        normalized_reason = (self.sanitize_evidence_text(reason) or "").strip()
        if len(normalized_reason) < 2 or len(normalized_reason) > 200:
            raise ValueError("Ignore reason must contain 2 to 200 characters")
        now = time.time()
        async with self._session_maker() as session:
            problem = await session.get(ProblemRecord, problem_id)
            if not problem:
                raise LookupError("Problem not found")
            if problem.state not in {"open", "in_progress", "waiting"}:
                raise ValueError("Problem cannot be ignored in its current state")
            problem.state = "ignored"
            problem.ignored_reason = normalized_reason
            problem.ignored_at = now
            problem.resolved_at = None
            problem.resolution_verification = "manually_ignored"
            session.add(
                ProblemActionRecord(
                    id=str(uuid.uuid4()),
                    problem_id=problem.id,
                    action_key="ignore_problem",
                    requested_at=now,
                    started_at=now,
                    finished_at=now,
                    result="accepted",
                    verification_result="manually_ignored",
                )
            )
            await session.commit()
            await session.refresh(problem)
            return self._to_item(problem)

    async def restore_problem(self, problem_id: str) -> ProblemItem:
        now = time.time()
        async with self._session_maker() as session:
            problem = await session.get(ProblemRecord, problem_id)
            if not problem:
                raise LookupError("Problem not found")
            if problem.state != "ignored":
                raise ValueError("Problem is not ignored")
            problem.state = "open"
            problem.ignored_reason = None
            problem.ignored_at = None
            problem.resolved_at = None
            problem.resolution_verification = "manually_restored"
            session.add(
                ProblemActionRecord(
                    id=str(uuid.uuid4()),
                    problem_id=problem.id,
                    action_key="restore_problem",
                    requested_at=now,
                    started_at=now,
                    finished_at=now,
                    result="accepted",
                    verification_result="manually_restored",
                )
            )
            await session.commit()
            await session.refresh(problem)
            return self._to_item(problem)

    async def verify_problem(self, problem_id: str) -> ProblemItem | None:
        async with self._session_maker() as session:
            problem = await session.get(ProblemRecord, problem_id)
            if not problem:
                return None
            verification = "not_verified"
            resolved = False
            if problem.object_kind == "conflict":
                occurrence_rows = await session.execute(
                    select(ProblemOccurrence.source_id)
                    .where(ProblemOccurrence.problem_id == problem.id)
                    .where(ProblemOccurrence.source_kind == "conflict")
                    .order_by(ProblemOccurrence.occurred_at.desc())
                    .limit(1)
                )
                conflict_id = occurrence_rows.scalar_one_or_none()
                conflict = await session.get(ConflictRecord, conflict_id) if conflict_id else None
                resolved = bool(conflict and conflict.resolved)
                verification = "source_resolved" if resolved else "not_verified"
            elif problem.resolution_key:
                recovery_row = await session.execute(
                    select(ProblemRecoveryFact)
                    .where(ProblemRecoveryFact.resolution_key == problem.resolution_key)
                    .where(ProblemRecoveryFact.occurred_at > problem.last_seen_at)
                    .order_by(ProblemRecoveryFact.occurred_at.desc())
                    .limit(1)
                )
                recovery = recovery_row.scalar_one_or_none()
                resolved = recovery is not None
                if recovery is not None:
                    verification = "same_object_operation_succeeded"
                    problem.resolved_by_run_id = recovery.run_id
                    problem.resolved_by_event_id = recovery.event_id
                    problem.last_good_at = recovery.occurred_at
            problem.resolution_verification = verification
            if resolved:
                problem.state = "resolved"
                problem.resolved_at = time.time()
                problem.ignored_reason = None
                problem.ignored_at = None
            elif problem.state in {"in_progress", "waiting"}:
                problem.state = "open"
                problem.resolved_at = None
            await session.commit()
            await session.refresh(problem)
            return self._to_item(problem)

    async def _ingest_event(
        self,
        session: AsyncSession,
        event: SyncRunEvent,
        *,
        task_root: str | None,
        operation_hint: str | None = None,
        occurrence_known_absent: bool = False,
        problems_by_fingerprint: dict[str, ProblemRecord] | None = None,
    ) -> None:
        occurrence_id = self._occurrence_id("sync_event", event.id)
        if not occurrence_known_absent and await session.get(ProblemOccurrence, occurrence_id):
            return
        object_path, object_key = self.normalize_object_path(event.path, task_root)
        classification = self.classify_event(
            event.status,
            event.path,
            event.message,
            operation_hint=operation_hint,
        )
        operation_family = self.operation_family_for_problem(classification.category, event.status)
        resolution_key = self.build_resolution_key(
            task_id=event.task_id,
            object_key=object_key,
            operation_family=operation_family,
        )
        fingerprint = self.build_fingerprint(
            source_kind="sync_event",
            task_id=event.task_id,
            category=classification.category,
            stage=event.status,
            normalized_error_code=classification.normalized_error_code,
            object_key=object_key,
        )
        problem = problems_by_fingerprint.get(fingerprint) if problems_by_fingerprint is not None else None
        if problem is None and problems_by_fingerprint is None:
            problem = (
                await session.execute(
                    select(ProblemRecord).where(ProblemRecord.fingerprint == fingerprint)
                )
            ).scalar_one_or_none()
        if not problem:
            problem = ProblemRecord(
                id=str(uuid.uuid4()),
                fingerprint=fingerprint,
                category=classification.category,
                severity=classification.severity,
                state="open",
                title=classification.title,
                summary=classification.summary,
                task_id=event.task_id,
                object_kind=self.event_object_kind(event.path, task_root),
                object_key=object_key,
                object_path=object_path,
                first_seen_at=event.timestamp,
                last_seen_at=event.timestamp,
                occurrence_count=0,
                latest_run_id=event.run_id,
                latest_event_id=event.id,
                classifier_version=CLASSIFIER_VERSION,
                resolution_key=resolution_key,
                operation_family=operation_family,
                actionability=self.actionability_for_category(classification.category),
            )
            session.add(problem)
            if problems_by_fingerprint is not None:
                problems_by_fingerprint[fingerprint] = problem
        elif problem.state == "resolved" and event.timestamp > problem.last_seen_at:
            problem.state = "open"
            problem.resolved_at = None
            problem.resolution_verification = "reopened_by_occurrence"
            problem.resolved_by_run_id = None
            problem.resolved_by_event_id = None
            problem.last_good_at = None
        problem.resolution_key = resolution_key
        problem.operation_family = operation_family
        problem.actionability = self.actionability_for_category(classification.category)
        problem.classifier_version = CLASSIFIER_VERSION
        problem.last_seen_at = max(problem.last_seen_at, event.timestamp)
        problem.occurrence_count += 1
        problem.latest_run_id = event.run_id
        problem.latest_event_id = event.id
        problem.object_path = object_path
        session.add(
            ProblemOccurrence(
                id=occurrence_id,
                problem_id=problem.id,
                source_kind="sync_event",
                source_id=event.id,
                run_id=event.run_id,
                event_id=event.id,
                occurred_at=event.timestamp,
                evidence_json=json.dumps(
                    {
                        "status": event.status,
                        "path": object_path,
                        "message": self.sanitize_evidence_text(event.message),
                        "task_name": event.task_name,
                    },
                    ensure_ascii=False,
                ),
            )
        )

    async def _ingest_recovery_event(
        self,
        session: AsyncSession,
        event: SyncRunEvent,
        *,
        task_root: str | None,
    ) -> None:
        if await session.get(ProblemRecoveryFact, event.id):
            return
        operation_family = self.operation_family_for_recovery(event.status)
        if operation_family is None:
            return
        _, object_key = self.normalize_object_path(event.path, task_root)
        resolution_key = self.build_resolution_key(
            task_id=event.task_id,
            object_key=object_key,
            operation_family=operation_family,
        )
        session.add(
            ProblemRecoveryFact(
                event_id=event.id,
                task_id=event.task_id,
                resolution_key=resolution_key,
                operation_family=operation_family,
                run_id=event.run_id,
                occurred_at=event.timestamp,
                created_at=time.time(),
            )
        )
        rows = await session.execute(
            select(ProblemRecord)
            .where(ProblemRecord.resolution_key == resolution_key)
            .where(ProblemRecord.state.in_(["open", "in_progress", "waiting", "ignored"]))
            .where(ProblemRecord.last_seen_at < event.timestamp)
        )
        for problem in rows.scalars().all():
            problem.state = "resolved"
            problem.resolved_at = event.timestamp
            problem.last_good_at = event.timestamp
            problem.resolved_by_run_id = event.run_id
            problem.resolved_by_event_id = event.id
            problem.resolution_verification = "same_object_operation_succeeded"
            problem.ignored_reason = None
            problem.ignored_at = None

    def _backfill_lifecycle_fields(self, problems: list[ProblemRecord]) -> None:
        for problem in problems:
            operation_family = problem.operation_family or self.operation_family_for_problem(
                problem.category,
                "conflict" if problem.object_kind == "conflict" else "failed",
            )
            problem.operation_family = operation_family
            problem.resolution_key = problem.resolution_key or self.build_resolution_key(
                task_id=problem.task_id or "",
                object_key=problem.object_key,
                operation_family=operation_family,
            )
            problem.actionability = self.actionability_for_category(problem.category)

    async def _resolve_legacy_delete_pending(
        self,
        session: AsyncSession,
        problems: list[ProblemRecord],
    ) -> None:
        candidates = [
            problem
            for problem in problems
            if problem.category == "deletion"
            and problem.state in {"open", "in_progress", "waiting"}
            and problem.latest_event_id
        ]
        if not candidates:
            return
        rows = await session.execute(
            select(SyncRunEvent.id, SyncRunEvent.status).where(
                SyncRunEvent.id.in_([problem.latest_event_id for problem in candidates])
            )
        )
        statuses = {str(event_id): str(status).strip().lower() for event_id, status in rows.all()}
        for problem in candidates:
            if statuses.get(str(problem.latest_event_id)) != "delete_pending":
                continue
            problem.state = "resolved"
            problem.resolved_at = problem.last_seen_at
            problem.last_good_at = problem.last_seen_at
            problem.resolution_verification = "workflow_state_not_problem"
            problem.actionability = "diagnostic_only"

    @staticmethod
    def operation_family_for_problem(category: str, stage: str) -> str:
        if category == "upload":
            return "upload"
        if category == "download":
            return "download"
        if category == "conversion":
            return "conversion"
        if category == "deletion" or stage == "delete_failed":
            return "delete"
        if category == "conflict":
            return "conflict"
        if category == "auth_permission":
            return "task_auth"
        if stage == "cancelled":
            return "task_run"
        return "diagnostic"

    @staticmethod
    def operation_family_for_recovery(status: str) -> str | None:
        return {
            "uploaded": "upload",
            "created": "upload",
            "linked": "upload",
            "mirrored": "upload",
            "downloaded": "download",
            "deleted": "delete",
        }.get(status.strip().lower())

    @staticmethod
    def actionability_for_category(category: str) -> str:
        if category == "conflict":
            return "manual_required"
        if category in {"upload", "download", "conversion", "network_remote", "local_io"}:
            return "auto_recovering"
        if category == "auth_permission":
            return "manual_required"
        return "diagnostic_only"

    @staticmethod
    def build_resolution_key(*, task_id: str, object_key: str, operation_family: str) -> str:
        raw = "|".join((task_id.strip().lower(), object_key.strip().lower(), operation_family))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _ingest_conflict(
        self,
        session: AsyncSession,
        conflict: ConflictRecord,
        *,
        task_roots: dict[str, str],
        existing_problem_id: str | None = None,
    ) -> None:
        occurrence_id = self._occurrence_id("conflict", conflict.id)
        if existing_problem_id is not None or await session.get(ProblemOccurrence, occurrence_id):
            if existing_problem_id is not None:
                problem = await session.get(ProblemRecord, existing_problem_id)
            else:
                problem_row = await session.execute(
                    select(ProblemRecord)
                    .join(ProblemOccurrence, ProblemOccurrence.problem_id == ProblemRecord.id)
                    .where(ProblemOccurrence.id == occurrence_id)
                )
                problem = problem_row.scalar_one_or_none()
            if problem and conflict.resolved and problem.state != "resolved":
                problem.state = "resolved"
                problem.resolved_at = conflict.resolved_at or time.time()
                problem.resolution_verification = "source_resolved"
                problem.ignored_reason = None
                problem.ignored_at = None
            return
        task_id, task_root = self._match_task(conflict.local_path, task_roots)
        object_path, object_key = self.normalize_object_path(conflict.local_path, task_root)
        fingerprint = self.build_fingerprint(
            source_kind="conflict",
            task_id=task_id or "",
            category="conflict",
            stage="version_diverged",
            normalized_error_code="conflict",
            object_key=object_key,
        )
        resolution_key = self.build_resolution_key(
            task_id=task_id or "",
            object_key=object_key,
            operation_family="conflict",
        )
        problem = (
            await session.execute(
                select(ProblemRecord).where(ProblemRecord.fingerprint == fingerprint)
            )
        ).scalar_one_or_none()
        if not problem:
            problem = ProblemRecord(
                id=str(uuid.uuid4()),
                fingerprint=fingerprint,
                category="conflict",
                severity="high",
                state="resolved" if conflict.resolved else "open",
                title=f"内容冲突 · {self._display_name(object_path)}",
                summary="本地和云端在同一同步基线后都发生变化，需要选择保留版本。",
                task_id=task_id,
                object_kind="conflict",
                object_key=object_key,
                object_path=object_path,
                first_seen_at=conflict.created_at,
                last_seen_at=conflict.created_at,
                occurrence_count=0,
                classifier_version=CLASSIFIER_VERSION,
                resolution_verification="source_resolved" if conflict.resolved else None,
                resolved_at=conflict.resolved_at if conflict.resolved else None,
                resolution_key=resolution_key,
                operation_family="conflict",
                actionability="manual_required",
                last_good_at=conflict.resolved_at if conflict.resolved else None,
            )
            session.add(problem)
            await session.flush()
        problem.last_seen_at = max(problem.last_seen_at, conflict.created_at)
        problem.occurrence_count += 1
        session.add(
            ProblemOccurrence(
                id=occurrence_id,
                problem_id=problem.id,
                source_kind="conflict",
                source_id=conflict.id,
                run_id=None,
                event_id=None,
                occurred_at=conflict.created_at,
                evidence_json=json.dumps(
                    {
                        "local_path": object_path,
                        "cloud_token": self._mask_token(conflict.cloud_token),
                        "local_hash": conflict.local_hash,
                        "db_hash": conflict.db_hash,
                        "cloud_version": conflict.cloud_version,
                        "db_version": conflict.db_version,
                    },
                    ensure_ascii=False,
                ),
            )
        )

    @classmethod
    def classify_event(
        cls,
        status: str,
        path: str,
        message: str | None,
        *,
        operation_hint: str | None = None,
    ) -> _Classification:
        text = f"{status} {path} {message or ''}".lower()
        status_key = status.strip().lower()
        error_code = cls.normalize_error_code(text, status_key)
        name = cls._display_name(path)
        if status_key == "conflict":
            return _Classification("conflict", "high", f"内容冲突 · {name}", "本地和云端均有变化，需要选择保留版本。", error_code)
        if status_key == "delete_pending":
            return _Classification("deletion", "low", f"待删除 · {name}", "对象正在安全删除宽限期内等待。", error_code)
        if status_key == "delete_failed":
            return _Classification("deletion", "medium", f"删除失败 · {name}", "删除动作未完成，需要确认目标状态或权限。", error_code)
        if status_key == "cancelled":
            return _Classification("system", "low", f"运行已中断 · {name}", "同步运行未完成，可能由退出、更新或手动停止触发。", error_code)
        if any(
            word in text
            for word in (
                "授权",
                "oauth",
                "refresh token",
                "refresh_token",
                "token is invalid",
                "code=20026",
                "code=20064",
                "code=20073",
                "scope",
                "forbidden",
                "permission",
                " 401",
                " 403",
            )
        ):
            return _Classification("auth_permission", "high", f"授权或权限异常 · {name}", "当前身份或应用权限不足以完成同步动作。", error_code)
        if any(word in text for word in ("上传", "upload", "blocks/", "/children", "云端写入")):
            return _Classification("upload", "high", f"上传失败 · {name}", "文件或文档内容没有成功写入云端。", error_code)
        if any(word in text for word in ("下载", "download", "写回本地")):
            return _Classification("download", "medium", f"下载失败 · {name}", "云端内容没有成功写入本地。", error_code)
        if any(word in text for word in ("convert", "conversion", "转换", "转码", "导入")):
            return _Classification("conversion", "medium", f"转换失败 · {name}", "格式转换或导入流程没有完成。", error_code)
        if any(word in text for word in ("占用", "locked", "winerror", "磁盘", "本地路径", "no such file")):
            return _Classification("local_io", "medium", f"本地文件异常 · {name}", "本地路径、文件占用、权限或磁盘状态阻止了同步。", error_code)
        if any(word in text for word in ("timeout", "timed out", " 429", " 500", " 502", " 503", " 504", "网络", "限流")):
            return _Classification("network_remote", "medium", f"网络或云端异常 · {name}", "网络连接、限流或飞书临时错误导致同步失败。", error_code)
        if operation_hint == "upload":
            return _Classification("upload", "high", f"上传失败 · {name}", "文件或文档内容没有成功写入云端。", error_code)
        if operation_hint == "download":
            return _Classification("download", "medium", f"下载失败 · {name}", "云端内容没有成功写入本地。", error_code)
        return _Classification("system", "medium", f"同步失败 · {name}", "同步动作未完成，需要查看原始证据。", error_code)

    @staticmethod
    def normalize_error_code(text: str, fallback: str) -> str:
        patterns = (
            r"\bhttp\s*[:=]?\s*(\d{3})\b",
            r"\bstatus\s*[:=]\s*(\d{3})\b",
            r"\bcode\s*[:=]\s*([a-z0-9_-]+)",
            r"\b(17\d{5,})\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return fallback.strip().lower() or "unknown"

    @staticmethod
    def normalize_object_path(path: str, task_root: str | None) -> tuple[str, str]:
        normalized = (path or "").strip().replace("\\", "/")
        normalized = re.sub(r"/+", "/", normalized)
        root = (task_root or "").strip().replace("\\", "/").rstrip("/")
        if root and normalized.lower().startswith(root.lower() + "/"):
            normalized = normalized[len(root) + 1 :]
        display = normalized.lstrip("/") or "未知对象"
        return display, display.casefold()

    @staticmethod
    def build_fingerprint(
        *,
        source_kind: str,
        task_id: str,
        category: str,
        stage: str,
        normalized_error_code: str,
        object_key: str,
    ) -> str:
        payload = "||".join(
            value.strip().casefold()
            for value in (
                source_kind,
                task_id,
                category,
                stage,
                normalized_error_code,
                object_key,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def sanitize_evidence_text(value: str | None) -> str | None:
        if value is None:
            return None
        sanitized = _REQUEST_ID_PATTERN.sub("请求标识已脱敏", value)
        sanitized = _TOKEN_PATTERN.sub("敏感凭据已脱敏", sanitized)
        return sanitized

    @staticmethod
    def _occurrence_id(source_kind: str, source_id: str) -> str:
        return hashlib.sha256(f"{source_kind}||{source_id}".encode("utf-8")).hexdigest()

    @staticmethod
    def _display_name(path: str) -> str:
        normalized = (path or "未知对象").replace("\\", "/").rstrip("/")
        return normalized.rsplit("/", 1)[-1] or "未知对象"

    @staticmethod
    def _match_task(path: str, task_roots: dict[str, str]) -> tuple[str | None, str | None]:
        normalized = path.replace("\\", "/").casefold()
        candidates = [
            (task_id, root)
            for task_id, root in task_roots.items()
            if normalized.startswith(root.replace("\\", "/").rstrip("/").casefold() + "/")
            or normalized == root.replace("\\", "/").rstrip("/").casefold()
        ]
        if not candidates:
            return None, None
        return max(candidates, key=lambda item: len(item[1]))

    @staticmethod
    def _mask_token(value: str) -> str:
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}***{value[-4:]}"

    def _to_item(self, record: ProblemRecord) -> ProblemItem:
        return ProblemItem(
            id=record.id,
            fingerprint=record.fingerprint,
            category=record.category,
            severity=record.severity,
            state=record.state,
            title=record.title,
            summary=record.summary,
            task_id=record.task_id,
            object_kind=record.object_kind,
            object_key=record.object_key,
            object_path=record.object_path,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            occurrence_count=record.occurrence_count,
            latest_run_id=record.latest_run_id,
            latest_event_id=record.latest_event_id,
            classifier_version=record.classifier_version,
            resolution_verification=record.resolution_verification,
            resolved_at=record.resolved_at,
            ignored_reason=record.ignored_reason,
            ignored_at=record.ignored_at,
            resolution_key=record.resolution_key,
            operation_family=record.operation_family,
            actionability=record.actionability,
            resolved_by_run_id=record.resolved_by_run_id,
            resolved_by_event_id=record.resolved_by_event_id,
            last_good_at=record.last_good_at,
            available_actions=self._available_actions(record),
        )

    @staticmethod
    def _to_occurrence(record: ProblemOccurrence) -> ProblemOccurrenceItem:
        return ProblemOccurrenceItem(**{column: getattr(record, column) for column in ProblemOccurrenceItem.__dataclass_fields__})

    @staticmethod
    def _to_action(record: ProblemActionRecord) -> ProblemActionItem:
        return ProblemActionItem(**{column: getattr(record, column) for column in ProblemActionItem.__dataclass_fields__})

    @staticmethod
    def _available_actions(record: ProblemRecord) -> tuple[AvailableProblemAction, ...]:
        if record.state in {"resolved", "ignored"}:
            return ()
        if record.object_kind == "conflict":
            return (
                AvailableProblemAction("use_cloud", "使用云端", "primary", True),
                AvailableProblemAction("use_local", "使用本地", "danger", True),
            )
        if record.task_id and record.actionability == "auto_recovering":
            actions = [AvailableProblemAction("retry_task", "重试任务", "primary")]
            if record.category == "local_io":
                actions.append(AvailableProblemAction("open_local_folder", "打开本地目录"))
            return tuple(actions)
        return ()


__all__ = [
    "AvailableProblemAction",
    "CLASSIFIER_VERSION",
    "ProblemActionItem",
    "ProblemItem",
    "ProblemOccurrenceItem",
    "ProblemReconcileResult",
    "ProblemRefreshResult",
    "ProblemService",
]
