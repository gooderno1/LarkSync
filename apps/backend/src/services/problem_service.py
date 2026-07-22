from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import (
    ConflictRecord,
    ProblemActionRecord,
    ProblemOccurrence,
    ProblemRecord,
    SyncRun,
    SyncRunEvent,
    SyncTask,
)
from src.db.session import get_session_maker


CLASSIFIER_VERSION = "problem-classifier-v1"
PROBLEM_STATUSES = {
    "failed",
    "delete_failed",
    "delete_pending",
    "cancelled",
}
_REQUEST_ID_PATTERN = re.compile(
    r"(?i)(?:request[_ -]?id|x-tt-logid|trace[_ -]?id)\s*[:=]\s*[^\s,;]+"
)
_TOKEN_PATTERN = re.compile(
    r"(?i)(?:access_token|refresh_token|app_secret|authorization)\s*[:=]\s*[^\s,;]+"
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
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._refresh_lock = asyncio.Lock()

    async def refresh_sources(self, *, event_limit: int | None = 1000) -> ProblemRefreshResult:
        async with self._refresh_lock:
            return await self._refresh_sources(event_limit=event_limit)

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

    async def _refresh_sources(self, *, event_limit: int | None) -> ProblemRefreshResult:
        async with self._session_maker() as session:
            task_rows = await session.execute(select(SyncTask.id, SyncTask.local_path))
            task_roots = {str(task_id): str(root) for task_id, root in task_rows.all()}
            unprocessed_event = and_(
                ProblemOccurrence.source_kind == "sync_event",
                ProblemOccurrence.source_id == SyncRunEvent.id,
            )
            event_stmt = (
                select(SyncRunEvent)
                .outerjoin(ProblemOccurrence, unprocessed_event)
                .where(func.lower(SyncRunEvent.status).in_(PROBLEM_STATUSES))
                .where(ProblemOccurrence.id.is_(None))
                .order_by(SyncRunEvent.timestamp.asc())
            )
            if event_limit is not None:
                event_stmt = event_stmt.limit(max(1, event_limit))
            event_rows = await session.execute(event_stmt)
            events = list(event_rows.scalars().all())
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
            problem_rows = await session.execute(select(ProblemRecord))
            problems_by_fingerprint = {
                record.fingerprint: record for record in problem_rows.scalars().all()
            }
            for event in events:
                await self._ingest_event(
                    session,
                    event,
                    task_root=task_roots.get(event.task_id),
                    occurrence_known_absent=True,
                    problems_by_fingerprint=problems_by_fingerprint,
                )
            for conflict in reversed(conflicts):
                await self._ingest_conflict(
                    session,
                    conflict,
                    task_roots=task_roots,
                    existing_problem_id=known_conflicts.get(conflict.id),
                )
            await session.commit()
        return ProblemRefreshResult(events_seen=len(events), conflicts_seen=len(conflicts))

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
            problem.resolution_verification = verification_result
            if result == "failed":
                problem.state = "open"
                problem.resolved_at = None
            elif verification_result in {"verified", "source_resolved", "later_run_succeeded"}:
                problem.state = "resolved"
                problem.resolved_at = now
            elif verification_result and verification_result.startswith("waiting"):
                problem.state = "waiting"
            elif action.action_key == "open_local_folder":
                problem.state = "open"
            else:
                problem.state = "waiting"
            await session.commit()
            await session.refresh(action)
            return self._to_action(action)

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
            elif problem.task_id:
                successful_run = await session.execute(
                    select(SyncRun.run_id)
                    .where(SyncRun.task_id == problem.task_id)
                    .where(SyncRun.state == "success")
                    .where(func.coalesce(SyncRun.finished_at, SyncRun.last_event_at, 0) > problem.last_seen_at)
                    .limit(1)
                )
                resolved = successful_run.scalar_one_or_none() is not None
                verification = "later_run_succeeded" if resolved else "not_verified"
            problem.resolution_verification = verification
            if resolved:
                problem.state = "resolved"
                problem.resolved_at = time.time()
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
        occurrence_known_absent: bool = False,
        problems_by_fingerprint: dict[str, ProblemRecord] | None = None,
    ) -> None:
        occurrence_id = self._occurrence_id("sync_event", event.id)
        if not occurrence_known_absent and await session.get(ProblemOccurrence, occurrence_id):
            return
        object_path, object_key = self.normalize_object_path(event.path, task_root)
        classification = self.classify_event(event.status, event.path, event.message)
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
                object_kind="sync_event",
                object_key=object_key,
                object_path=object_path,
                first_seen_at=event.timestamp,
                last_seen_at=event.timestamp,
                occurrence_count=0,
                latest_run_id=event.run_id,
                latest_event_id=event.id,
                classifier_version=CLASSIFIER_VERSION,
            )
            session.add(problem)
            if problems_by_fingerprint is not None:
                problems_by_fingerprint[fingerprint] = problem
        elif problem.state == "resolved" and event.timestamp > problem.last_seen_at:
            problem.state = "open"
            problem.resolved_at = None
            problem.resolution_verification = "reopened_by_occurrence"
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
        if any(word in text for word in ("授权", "oauth", "scope", "forbidden", "permission", " 401", " 403")):
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
        if record.state == "resolved":
            return ()
        if record.object_kind == "conflict":
            return (
                AvailableProblemAction("use_cloud", "使用云端", "primary", True),
                AvailableProblemAction("use_local", "使用本地", "danger", True),
            )
        if record.task_id and record.category not in {"deletion"}:
            return (
                AvailableProblemAction("retry_task", "重试任务", "primary"),
                AvailableProblemAction("open_local_folder", "打开本地目录"),
            )
        return ()


__all__ = [
    "AvailableProblemAction",
    "CLASSIFIER_VERSION",
    "ProblemActionItem",
    "ProblemItem",
    "ProblemOccurrenceItem",
    "ProblemRefreshResult",
    "ProblemService",
]
