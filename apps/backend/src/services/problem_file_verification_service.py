from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.account_context import account_scope
from src.core.config import ConfigManager
from src.db.models import (
    ConflictRecord, ProblemRecord, ProblemRecoveryFact, SyncLink, SyncRunEvent, SyncTask,
)
from src.db.session import get_session_maker
from src.services.file_downloader import FileDownloader
from src.services.file_hash import calculate_file_hash
from src.services.problem_service import ProblemReconcileResult, ProblemService
from src.services.sync_path_mode import PathSyncRule, path_supports_direction
from src.services.sync_path_policy import should_ignore_sync_path
from src.services.sync_task_service import SyncTaskItem


@dataclass(frozen=True)
class _Candidate:
    problem_id: str
    account_id: str
    task_id: str
    task_name: str
    last_seen_at: float
    latest_event_id: str | None
    occurrence_count: int
    path: Path
    cloud_token: str
    sha256: str
    size: int
    resolution_key: str


class ProblemFileVerificationService:
    """Recover binary-file upload problems from verified current content only."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        *,
        downloader_factory: Callable[[], FileDownloader] = FileDownloader,
        ignore_hidden_cache_paths: bool | None = None,
    ) -> None:
        self._sessions = session_maker or get_session_maker()
        self._downloader_factory = downloader_factory
        self._ignore_hidden_cache_paths = ignore_hidden_cache_paths
        self._cursor: tuple[float, str] | None = None
        self._lock = asyncio.Lock()

    async def reconcile(self, *, limit: int = 5) -> ProblemReconcileResult:
        async with self._lock:
            async with self._sessions() as session:
                query = (
                    select(ProblemRecord.id, ProblemRecord.last_seen_at)
                    .where(ProblemRecord.state.in_(["open", "waiting"]))
                    .where(ProblemRecord.object_kind == "sync_object")
                    .where(ProblemRecord.operation_family == "upload")
                    .order_by(ProblemRecord.last_seen_at, ProblemRecord.id)
                    .limit(max(1, min(20, limit)))
                )
                if self._cursor:
                    seen_at, problem_id = self._cursor
                    query = query.where(or_(
                        ProblemRecord.last_seen_at > seen_at,
                        (ProblemRecord.last_seen_at == seen_at) & (ProblemRecord.id > problem_id),
                    ))
                rows = (await session.execute(query)).all()
            self._cursor = (rows[-1].last_seen_at, rows[-1].id) if rows else None
            resolved = 0
            for problem_id, _ in rows:
                try:
                    async with self._sessions() as session:
                        candidate = await self._candidate(session, problem_id)
                    if candidate is None:
                        continue
                    # Use the start time so a concurrently recorded failure cannot
                    # be masked by an event timestamp taken after the download.
                    evidence_at = time.time()
                    if evidence_at <= candidate.last_seen_at:
                        continue
                    with account_scope(candidate.account_id):
                        downloader = self._downloader_factory()
                        try:
                            matches = await asyncio.wait_for(downloader.matches_file(
                                candidate.cloud_token,
                                expected_hash=candidate.sha256,
                                expected_size=candidate.size,
                            ), timeout=15.0)
                        finally:
                            await downloader.close()
                    if matches and await self._record_verified(candidate, evidence_at):
                        resolved += 1
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.debug(
                        "文件一致性核验暂未完成: problem_id={} error_type={}",
                        problem_id, type(exc).__name__,
                    )
            return ProblemReconcileResult(scanned=len(rows), resolved=resolved)

    async def _candidate(self, session: AsyncSession, problem_id: str) -> _Candidate | None:
        problem = await session.get(ProblemRecord, problem_id)
        if (
            problem is None or problem.state not in {"open", "waiting"}
            or problem.object_kind != "sync_object" or problem.operation_family != "upload"
            or not problem.object_path or not problem.resolution_key
        ):
            return None
        task = await session.get(SyncTask, problem.task_id)
        if task is None or not task.enabled or task.account_id != problem.account_id:
            return None
        root = Path(task.local_path).expanduser().resolve()
        path = (root / problem.object_path.replace("\\", "/")).resolve()
        if not path.is_relative_to(root) or path.suffix.lower() == ".md" or not path.is_file():
            return None
        ignored = json.loads(task.ignored_subpaths or "[]")
        task_item = SyncTaskItem(
            id=task.id, name=task.name, account_id=task.account_id,
            local_path=task.local_path, cloud_folder_token=task.cloud_folder_token,
            cloud_folder_name=task.cloud_folder_name, base_path=task.base_path,
            sync_mode=task.sync_mode, update_mode=task.update_mode, enabled=task.enabled,
            created_at=task.created_at, updated_at=task.updated_at, ignored_subpaths=ignored,
            path_sync_rules=[PathSyncRule.model_validate(item) for item in json.loads(task.path_sync_rules or "[]")],
        )
        ignore_hidden = self._ignore_hidden_cache_paths
        if ignore_hidden is None:
            ignore_hidden = ConfigManager.get().config.ignore_hidden_cache_paths
        if not path_supports_direction(task_item, path, "upload") or should_ignore_sync_path(
            task_root=task.local_path, path=path, ignored_subpaths=ignored,
            ignore_hidden_cache_paths=ignore_hidden,
        ):
            return None
        link = await session.get(SyncLink, (problem.account_id, str(path)))
        if (
            link is None or link.task_id != task.id or link.cloud_type != "file"
            or not link.cloud_token or not link.local_hash
            or link.local_size is None or link.local_size <= 0
        ):
            return None
        object_key = ProblemService.normalize_object_path(str(path), task.local_path)[1]
        if object_key != problem.object_key:
            return None
        conflicts = await session.execute(select(ConflictRecord.local_path).where(
            ConflictRecord.account_id == problem.account_id,
            ConflictRecord.resolved.is_(False),
        ))
        if any(
            ProblemService.normalize_object_path(value, task.local_path)[1] == object_key
            for value in conflicts.scalars()
        ):
            return None
        digest, size = await asyncio.to_thread(self._local_signature, path)
        if digest != link.local_hash or size != link.local_size:
            return None
        return _Candidate(
            problem.id, problem.account_id, task.id, task.name or task.local_path,
            problem.last_seen_at, problem.latest_event_id, problem.occurrence_count,
            path, link.cloud_token, digest, size, problem.resolution_key,
        )

    @staticmethod
    def _local_signature(path: Path) -> tuple[str, int]:
        return calculate_file_hash(path), path.stat().st_size

    async def _record_verified(self, candidate: _Candidate, evidence_at: float) -> bool:
        async with self._sessions() as session:
            # Re-read the failure, rules, link, conflicts and local bytes after I/O.
            if await self._candidate(session, candidate.problem_id) != candidate:
                return False
            event_id = uuid.uuid4().hex
            changed = await session.execute(update(ProblemRecord).where(
                ProblemRecord.id == candidate.problem_id,
                ProblemRecord.account_id == candidate.account_id,
                ProblemRecord.state.in_(["open", "waiting"]),
                ProblemRecord.last_seen_at == candidate.last_seen_at,
                ProblemRecord.latest_event_id == candidate.latest_event_id,
                ProblemRecord.occurrence_count == candidate.occurrence_count,
            ).values(
                state="resolved", resolved_at=evidence_at, last_good_at=evidence_at,
                resolved_by_run_id=None, resolved_by_event_id=event_id,
                resolution_verification="same_object_content_verified",
            ).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                return False
            session.add(SyncRunEvent(
                id=event_id, account_id=candidate.account_id, task_id=candidate.task_id,
                task_name=candidate.task_name, timestamp=evidence_at, status="upload_verified",
                path=str(candidate.path), message=json.dumps({
                    "verification": "same_object_content_verified",
                    "sha256": candidate.sha256, "size": candidate.size,
                    "cloud_token": candidate.cloud_token,
                }, ensure_ascii=False), created_at=time.time(),
            ))
            session.add(ProblemRecoveryFact(
                event_id=event_id, account_id=candidate.account_id, task_id=candidate.task_id,
                resolution_key=candidate.resolution_key, operation_family="upload",
                occurred_at=evidence_at, created_at=time.time(),
            ))
            await session.commit()
            return True
