from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncMeta, SyncRunEvent
from src.db.session import get_session_maker
from src.services.sync_event_store import SyncEventRecord, SyncEventStore

_BACKFILL_STATUS_KEY = "log_center_backfill_v1_status"
_BACKFILL_OFFSET_KEY = "log_center_backfill_v1_offset"
_BACKFILL_LOG_SIZE_KEY = "log_center_backfill_v1_log_size"
_BACKFILL_LOG_MTIME_NS_KEY = "log_center_backfill_v1_log_mtime_ns"


@dataclass(frozen=True)
class SyncRunEventAppendResult:
    inserted: int
    attempted: int
    succeeded: bool


@dataclass(frozen=True)
class SyncRunEventBackfillState:
    status: str
    offset: int
    log_size: int
    log_mtime_ns: int
    completed: bool


@dataclass(frozen=True)
class SyncRunEventBackfillResult:
    inserted: int
    skipped: int
    completed: bool
    offset: int
    file_size: int


class SyncRunEventService:
    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._last_pruned_at: float | None = None

    async def append_batch(self, records: Sequence[SyncEventRecord]) -> int:
        return (await self._append_batch_result(records)).inserted

    async def read_events(
        self,
        *,
        limit: int,
        offset: int,
        status: str,
        statuses: list[str] | None = None,
        search: str,
        task_id: str,
        task_ids: list[str] | None = None,
        run_id: str = "",
        run_ids: list[str] | None = None,
        order: str = "desc",
        suppress_errors: bool = True,
        since: float | None = None,
        until: float | None = None,
    ) -> tuple[int, list[SyncEventRecord]]:
        filters = self._build_filters(
            status=status,
            statuses=statuses,
            search=search,
            task_id=task_id,
            task_ids=task_ids,
            run_id=run_id,
            run_ids=run_ids,
            since=since,
            until=until,
        )
        order_normalized = order.strip().lower()
        if order_normalized not in {"asc", "desc"}:
            order_normalized = "desc"
        order_by = (
            (SyncRunEvent.timestamp.asc(), SyncRunEvent.created_at.asc())
            if order_normalized == "asc"
            else (SyncRunEvent.timestamp.desc(), SyncRunEvent.created_at.desc())
        )
        total_stmt = select(func.count()).select_from(SyncRunEvent)
        data_stmt = select(SyncRunEvent).limit(limit).offset(offset)
        if filters:
            total_stmt = total_stmt.where(*filters)
            data_stmt = data_stmt.where(*filters)
        data_stmt = data_stmt.order_by(*order_by)
        try:
            async with self._session_maker() as session:
                total = int((await session.execute(total_stmt)).scalar_one() or 0)
                result = await session.execute(data_stmt)
                records = [self._to_record(item) for item in result.scalars().all()]
                return total, records
        except SQLAlchemyError:
            logger.exception("运行事件查询失败")
            if suppress_errors:
                return 0, []
            raise

    async def prune(
        self,
        *,
        retention_days: int,
        min_interval_seconds: int = 300,
        batch_size: int = 1000,
    ) -> int:
        if retention_days <= 0:
            return 0
        now = time.time()
        if (
            self._last_pruned_at is not None
            and now - self._last_pruned_at < min_interval_seconds
        ):
            return 0
        self._last_pruned_at = now
        cutoff = now - retention_days * 86400
        removed = 0
        try:
            async with self._session_maker() as session:
                while True:
                    id_rows = await session.execute(
                        select(SyncRunEvent.id)
                        .where(SyncRunEvent.timestamp < cutoff)
                        .limit(batch_size)
                    )
                    ids = [row[0] for row in id_rows.all()]
                    if not ids:
                        break
                    await session.execute(delete(SyncRunEvent).where(SyncRunEvent.id.in_(ids)))
                    await session.commit()
                    removed += len(ids)
        except SQLAlchemyError:
            logger.exception("运行事件清理失败")
            return removed
        return removed

    async def backfill_step_from_event_store(
        self,
        event_store: SyncEventStore,
        *,
        batch_size: int = 200,
    ) -> SyncRunEventBackfillResult:
        safe_batch_size = max(1, int(batch_size or 1))
        state = await self.get_backfill_state(event_store)
        if state.log_size <= 0:
            await self._set_backfill_state(
                status="completed",
                offset=0,
                log_size=0,
                log_mtime_ns=state.log_mtime_ns,
            )
            return SyncRunEventBackfillResult(
                inserted=0,
                skipped=0,
                completed=True,
                offset=0,
                file_size=0,
            )
        if state.completed and state.offset >= state.log_size:
            await self._set_backfill_state(
                status="completed",
                offset=state.offset,
                log_size=state.log_size,
                log_mtime_ns=state.log_mtime_ns,
            )
            return SyncRunEventBackfillResult(
                inserted=0,
                skipped=0,
                completed=True,
                offset=state.offset,
                file_size=state.log_size,
            )

        batch: list[SyncEventRecord] = []
        next_offset = state.offset
        for frame in event_store.iter_frames(start_offset=state.offset):
            next_offset = frame.next_offset
            if frame.record is not None:
                batch.append(frame.record)
            if len(batch) >= safe_batch_size:
                break

        append_result = SyncRunEventAppendResult(
            inserted=0,
            attempted=0,
            succeeded=True,
        )
        if batch:
            append_result = await self._append_batch_result(batch)
            if not append_result.succeeded:
                await self._set_backfill_state(
                    status="running",
                    offset=state.offset,
                    log_size=state.log_size,
                    log_mtime_ns=state.log_mtime_ns,
                )
                return SyncRunEventBackfillResult(
                    inserted=0,
                    skipped=0,
                    completed=False,
                    offset=state.offset,
                    file_size=state.log_size,
                )

        completed = next_offset >= state.log_size
        await self._set_backfill_state(
            status="completed" if completed else "running",
            offset=next_offset,
            log_size=state.log_size,
            log_mtime_ns=state.log_mtime_ns,
        )
        return SyncRunEventBackfillResult(
            inserted=append_result.inserted,
            skipped=max(0, append_result.attempted - append_result.inserted),
            completed=completed,
            offset=next_offset,
            file_size=state.log_size,
        )

    async def backfill_from_event_store(
        self,
        event_store: SyncEventStore,
        *,
        batch_size: int = 200,
        max_steps: int | None = None,
    ) -> int:
        inserted = 0
        previous_offset: int | None = None
        steps = 0
        while max_steps is None or steps < max_steps:
            result = await self.backfill_step_from_event_store(
                event_store,
                batch_size=batch_size,
            )
            inserted += result.inserted
            steps += 1
            if result.completed:
                break
            if previous_offset == result.offset and result.inserted == 0 and result.skipped == 0:
                break
            previous_offset = result.offset
        return inserted

    async def fast_forward_backfill(self, event_store: SyncEventStore) -> None:
        """保留 JSONL，但将已经冗余的自动回填断点对齐到当前文件尾。"""
        current_size = event_store.file_size_bytes()
        await self._set_backfill_state(
            status="completed",
            offset=current_size,
            log_size=current_size,
            log_mtime_ns=event_store.file_mtime_ns(),
        )

    async def has_events(
        self,
        *,
        task_id: str = "",
        run_id: str = "",
    ) -> bool:
        filters = self._build_filters(
            status="",
            statuses=[],
            search="",
            task_id=task_id,
            task_ids=[],
            run_id=run_id,
            run_ids=[],
            since=None,
            until=None,
        )
        stmt = select(SyncRunEvent.id).limit(1)
        if filters:
            stmt = stmt.where(*filters)
        try:
            async with self._session_maker() as session:
                result = await session.execute(stmt)
                return result.scalar_one_or_none() is not None
        except SQLAlchemyError:
            logger.exception("运行事件存在性检查失败")
            return False

    async def get_backfill_state(
        self,
        event_store: SyncEventStore,
    ) -> SyncRunEventBackfillState:
        current_size = event_store.file_size_bytes()
        current_mtime_ns = event_store.file_mtime_ns()
        try:
            meta = await self._get_meta_values(
                [
                    _BACKFILL_STATUS_KEY,
                    _BACKFILL_OFFSET_KEY,
                    _BACKFILL_LOG_SIZE_KEY,
                    _BACKFILL_LOG_MTIME_NS_KEY,
                ]
            )
        except SQLAlchemyError:
            logger.exception("读取运行事件回填状态失败")
            return SyncRunEventBackfillState(
                status="pending",
                offset=0,
                log_size=current_size,
                log_mtime_ns=current_mtime_ns,
                completed=current_size <= 0,
            )

        raw_status = (meta.get(_BACKFILL_STATUS_KEY) or "pending").strip().lower()
        if raw_status not in {"pending", "running", "completed", "failed"}:
            raw_status = "pending"
        stored_offset = self._parse_int_meta(meta.get(_BACKFILL_OFFSET_KEY))
        stored_log_size = self._parse_int_meta(meta.get(_BACKFILL_LOG_SIZE_KEY))
        stored_log_mtime_ns = self._parse_int_meta(meta.get(_BACKFILL_LOG_MTIME_NS_KEY))
        normalized_offset = self._normalize_backfill_offset(
            stored_offset=stored_offset,
            stored_log_size=stored_log_size,
            stored_log_mtime_ns=stored_log_mtime_ns,
            current_size=current_size,
            current_mtime_ns=current_mtime_ns,
        )
        if normalized_offset != stored_offset:
            logger.info(
                "运行事件回填断点已重置: old_offset={} new_offset={} size={}",
                stored_offset,
                normalized_offset,
                current_size,
            )
        completed = current_size <= 0 or normalized_offset >= current_size
        status = "completed" if completed else raw_status
        if status == "completed" and not completed:
            status = "running"
        return SyncRunEventBackfillState(
            status=status,
            offset=normalized_offset,
            log_size=current_size,
            log_mtime_ns=current_mtime_ns,
            completed=completed,
        )

    async def _append_batch_result(
        self,
        records: Sequence[SyncEventRecord],
    ) -> SyncRunEventAppendResult:
        rows = [self._row_from_record(record) for record in records if self._is_record_valid(record)]
        attempted = len(rows)
        if not rows:
            return SyncRunEventAppendResult(inserted=0, attempted=0, succeeded=True)
        stmt = sqlite_insert(SyncRunEvent).values(rows).prefix_with("OR IGNORE")
        try:
            async with self._session_maker() as session:
                result = await session.execute(stmt)
                await session.commit()
                rowcount = max(int(result.rowcount or 0), 0)
                return SyncRunEventAppendResult(
                    inserted=rowcount,
                    attempted=attempted,
                    succeeded=True,
                )
        except SQLAlchemyError:
            logger.exception("运行事件批量写入失败")
            return SyncRunEventAppendResult(
                inserted=0,
                attempted=attempted,
                succeeded=False,
            )

    async def _get_meta_values(self, keys: Sequence[str]) -> dict[str, str]:
        if not keys:
            return {}
        async with self._session_maker() as session:
            result = await session.execute(
                select(SyncMeta.key, SyncMeta.value).where(SyncMeta.key.in_(list(keys)))
            )
            return {str(key): str(value or "") for key, value in result.all()}

    async def _set_backfill_state(
        self,
        *,
        status: str,
        offset: int,
        log_size: int,
        log_mtime_ns: int,
    ) -> None:
        await self._set_meta_values(
            {
                _BACKFILL_STATUS_KEY: status,
                _BACKFILL_OFFSET_KEY: str(max(0, int(offset))),
                _BACKFILL_LOG_SIZE_KEY: str(max(0, int(log_size))),
                _BACKFILL_LOG_MTIME_NS_KEY: str(max(0, int(log_mtime_ns))),
            }
        )

    async def _set_meta_values(self, values: dict[str, str]) -> None:
        if not values:
            return
        now = time.time()
        rows = [
            {
                "key": key,
                "value": value,
                "updated_at": now,
            }
            for key, value in values.items()
        ]
        stmt = sqlite_insert(SyncMeta)
        stmt = stmt.values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SyncMeta.key],
            set_={
                "value": stmt.excluded.value,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        async with self._session_maker() as session:
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    def _parse_int_meta(raw: str | None) -> int:
        try:
            return max(0, int(raw or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _normalize_backfill_offset(
        *,
        stored_offset: int,
        stored_log_size: int,
        stored_log_mtime_ns: int,
        current_size: int,
        current_mtime_ns: int,
    ) -> int:
        if current_size <= 0:
            return 0
        if stored_offset < 0 or stored_offset > current_size:
            return 0
        if stored_log_size > current_size:
            return 0
        if (
            stored_log_size == current_size
            and stored_log_size > 0
            and stored_log_mtime_ns > 0
            and current_mtime_ns > 0
            and stored_log_mtime_ns != current_mtime_ns
        ):
            return 0
        return stored_offset

    @staticmethod
    def build_event_id(record: SyncEventRecord) -> str:
        payload = "||".join(
            [
                f"{record.timestamp:.6f}",
                record.task_id,
                record.task_name,
                record.status,
                record.path,
                record.message or "",
                record.run_id or "",
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_record_valid(record: SyncEventRecord) -> bool:
        return bool(record.task_id and record.status and record.path)

    @classmethod
    def _row_from_record(cls, record: SyncEventRecord) -> dict[str, object]:
        now = time.time()
        return {
            "id": cls.build_event_id(record),
            "task_id": record.task_id,
            "task_name": record.task_name or "未命名任务",
            "run_id": record.run_id,
            "timestamp": float(record.timestamp),
            "status": record.status,
            "path": record.path,
            "message": record.message,
            "created_at": now,
        }

    @staticmethod
    def _to_record(item: SyncRunEvent) -> SyncEventRecord:
        return SyncEventRecord(
            timestamp=float(item.timestamp),
            task_id=item.task_id,
            task_name=item.task_name,
            status=item.status,
            path=item.path,
            message=item.message,
            run_id=item.run_id,
        )

    @staticmethod
    def _build_filters(
        *,
        status: str,
        statuses: list[str] | None,
        search: str,
        task_id: str,
        task_ids: list[str] | None,
        run_id: str,
        run_ids: list[str] | None,
        since: float | None = None,
        until: float | None = None,
    ) -> list[object]:
        filters: list[object] = []
        status_filters = {
            value.strip().lower()
            for value in ([status] if status else []) + list(statuses or [])
            if value and value.strip()
        }
        task_filters = {
            value.strip()
            for value in ([task_id] if task_id else []) + list(task_ids or [])
            if value and value.strip()
        }
        run_filters = {
            value.strip()
            for value in ([run_id] if run_id else []) + list(run_ids or [])
            if value and value.strip()
        }
        if status_filters:
            filters.append(func.lower(SyncRunEvent.status).in_(status_filters))
        if task_filters:
            filters.append(SyncRunEvent.task_id.in_(task_filters))
        if run_filters:
            filters.append(func.coalesce(SyncRunEvent.run_id, "").in_(run_filters))
        if since is not None:
            filters.append(SyncRunEvent.timestamp >= float(since))
        if until is not None:
            filters.append(SyncRunEvent.timestamp <= float(until))
        search_filter = search.strip().lower()
        if search_filter:
            pattern = f"%{search_filter}%"
            filters.append(
                or_(
                    func.lower(SyncRunEvent.task_name).like(pattern),
                    func.lower(SyncRunEvent.path).like(pattern),
                    func.lower(func.coalesce(SyncRunEvent.message, "")).like(pattern),
                    func.lower(func.coalesce(SyncRunEvent.run_id, "")).like(pattern),
                )
            )
        return filters


__all__ = [
    "SyncRunEventAppendResult",
    "SyncRunEventBackfillResult",
    "SyncRunEventBackfillState",
    "SyncRunEventService",
]
