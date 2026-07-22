from __future__ import annotations

from loguru import logger

from src.api.sync_task_models import (
    SyncFileEventResponse,
    SyncLogEntry,
    SyncLogResponse,
    SyncTaskDiagnosticCounts,
    SyncTaskCheckStateResponse,
    SyncTaskDiagnosticsResponse,
    SyncTaskOverviewResponse,
    SyncTaskResponse,
    SyncTaskRunSummaryResponse,
    SyncTaskStatusResponse,
)
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_run_event_service import (
    SyncRunEventBackfillState,
    SyncRunEventService,
)
from src.services.sync_run_service import SyncRunItem, SyncRunService
from src.services.sync_runner import SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem
from src.services.sync_task_check_state_service import (
    SyncTaskCheckStateItem,
    SyncTaskCheckStateService,
)

PROBLEM_STATUSES = {"failed", "delete_failed", "conflict", "cancelled"}
TERMINAL_STATUSES = {"success", "failed", "cancelled"}
CURRENT_FILE_EXCLUDED_STATUSES = {"started", "success", "failed", "cancelled"}


def sync_log_entry_from_record(record: SyncEventRecord) -> SyncLogEntry:
    return SyncLogEntry(
        event_id=SyncRunEventService.build_event_id(record),
        task_id=record.task_id,
        task_name=record.task_name,
        timestamp=record.timestamp,
        status=record.status,
        path=record.path,
        message=record.message,
        run_id=record.run_id,
    )


async def get_persisted_run_event_backfill_state(
    *,
    run_event_service: SyncRunEventService,
    event_store: SyncEventStore,
) -> SyncRunEventBackfillState | None:
    try:
        return await run_event_service.get_backfill_state(event_store)
    except Exception:
        logger.exception("读取运行事件回填状态失败")
        return None


async def read_sync_events_db_first(
    *,
    run_event_service: SyncRunEventService,
    event_store: SyncEventStore,
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
    since: float | None = None,
    until: float | None = None,
) -> tuple[int, list[SyncEventRecord]]:
    backfill_state = await get_persisted_run_event_backfill_state(
        run_event_service=run_event_service,
        event_store=event_store,
    )
    try:
        total, records = await run_event_service.read_events(
            limit=limit,
            offset=offset,
            status=status,
            statuses=statuses,
            search=search,
            task_id=task_id,
            task_ids=task_ids,
            run_id=run_id,
            run_ids=run_ids,
            order=order,
            suppress_errors=False,
            since=since,
            until=until,
        )
    except Exception:
        logger.exception("运行事件数据库查询失败，回退 JSONL")
        return event_store.read_events(
            limit=limit,
            offset=offset,
            status=status,
            statuses=statuses,
            search=search,
            task_id=task_id,
            task_ids=task_ids,
            run_id=run_id,
            run_ids=run_ids,
            order=order,
            since=since,
            until=until,
        )

    if total > 0:
        return total, records

    if backfill_state is not None and backfill_state.completed:
        return total, records

    logger.debug(
        "运行事件回填未完成，回退读取 sync-events.jsonl: task_id={} run_id={} search={}",
        task_id,
        run_id,
        search,
    )
    return event_store.read_events(
        limit=limit,
        offset=offset,
        status=status,
        statuses=statuses,
        search=search,
        task_id=task_id,
        task_ids=task_ids,
        run_id=run_id,
        run_ids=run_ids,
        order=order,
        since=since,
        until=until,
    )


def current_file_from_status(status: SyncTaskStatus) -> SyncFileEventResponse | None:
    for event in reversed(status.last_files):
        if event.status not in CURRENT_FILE_EXCLUDED_STATUSES:
            return SyncFileEventResponse.from_event(event)
    return None


def file_event_from_record(record: SyncEventRecord) -> SyncFileEventResponse:
    return SyncFileEventResponse(
        path=record.path,
        status=record.status,
        message=record.message,
        timestamp=record.timestamp,
    )


def current_file_from_records(records: list[SyncEventRecord]) -> SyncFileEventResponse | None:
    for record in records:
        if record.status not in CURRENT_FILE_EXCLUDED_STATUSES:
            return file_event_from_record(record)
    return None


def build_run_counts(
    *,
    event_counts: dict[str, int],
    status: SyncTaskStatus | None,
) -> SyncTaskDiagnosticCounts:
    uploaded = event_counts.get("uploaded", 0)
    downloaded = event_counts.get("downloaded", 0)
    deleted = event_counts.get("deleted", 0)
    failed = event_counts.get("failed", 0)
    delete_failed = event_counts.get("delete_failed", 0)
    skipped = event_counts.get("skipped", 0)
    conflicts = event_counts.get("conflict", 0)
    delete_pending = event_counts.get("delete_pending", 0)
    derived_completed = uploaded + downloaded + deleted
    derived_failed = failed + delete_failed
    derived_processed = (
        derived_completed
        + derived_failed
        + skipped
        + conflicts
        + delete_pending
    )
    if status is None:
        total = derived_processed
        completed = derived_completed
        failed_value = derived_failed
        skipped_value = skipped
        processed = derived_processed
    else:
        uploaded = max(uploaded, status.uploaded_files)
        downloaded = max(downloaded, status.downloaded_files)
        deleted = max(deleted, status.deleted_files)
        conflicts = max(conflicts, status.conflict_files)
        delete_pending = max(delete_pending, status.delete_pending_files)
        delete_failed = max(delete_failed, status.delete_failed_files)
        total = max(status.total_files, derived_processed)
        completed = max(status.completed_files, derived_completed)
        failed_value = max(status.failed_files, derived_failed)
        skipped_value = max(status.skipped_files, skipped)
        processed = max(
            status.completed_files + status.failed_files + status.skipped_files,
            derived_processed,
        )
    return SyncTaskDiagnosticCounts(
        total=total,
        processed=processed,
        completed=completed,
        failed=failed_value,
        skipped=skipped_value,
        uploaded=uploaded,
        downloaded=downloaded,
        deleted=deleted,
        conflicts=conflicts,
        delete_pending=delete_pending,
        delete_failed=delete_failed,
    )


def derive_run_state(records: list[SyncEventRecord], live_status: SyncTaskStatus | None) -> str:
    if live_status is not None:
        return live_status.state
    for record in records:
        if record.status in TERMINAL_STATUSES:
            return record.status
    if any(record.status in PROBLEM_STATUSES for record in records):
        return "failed"
    if records:
        return "success"
    return "idle"


def build_run_summary(
    *,
    run_id: str,
    records: list[SyncEventRecord],
    live_status: SyncTaskStatus | None = None,
) -> SyncTaskRunSummaryResponse:
    ordered_records = sorted(records, key=lambda item: item.timestamp, reverse=True)
    event_counts: dict[str, int] = {}
    for record in ordered_records:
        event_counts[record.status] = event_counts.get(record.status, 0) + 1
    started_record = next(
        (record for record in reversed(ordered_records) if record.status == "started"),
        None,
    )
    finished_record = next(
        (record for record in ordered_records if record.status in TERMINAL_STATUSES),
        None,
    )
    last_problem = next(
        (record for record in ordered_records if record.status in PROBLEM_STATUSES),
        None,
    )
    counts = build_run_counts(event_counts=event_counts, status=live_status)
    state = derive_run_state(ordered_records, live_status)
    started_at = (
        live_status.started_at
        if live_status and live_status.started_at is not None
        else (
            started_record.timestamp
            if started_record
            else (ordered_records[-1].timestamp if ordered_records else None)
        )
    )
    finished_at = (
        live_status.finished_at
        if live_status and live_status.finished_at is not None
        else (
            finished_record.timestamp
            if finished_record
            else (
                None
                if state == "running"
                else (ordered_records[0].timestamp if ordered_records else None)
            )
        )
    )
    current_file = (
        current_file_from_status(live_status)
        if live_status is not None
        else current_file_from_records(ordered_records)
    )
    problem_count = sum(
        count for event_status, count in event_counts.items() if event_status in PROBLEM_STATUSES
    )
    last_error = (
        live_status.last_error
        if live_status and live_status.last_error
        else (last_problem.message if last_problem else None)
    )
    return SyncTaskRunSummaryResponse(
        run_id=run_id,
        state=state,
        started_at=started_at,
        finished_at=finished_at,
        last_event_at=ordered_records[0].timestamp if ordered_records else (
            live_status.finished_at or live_status.started_at if live_status else None
        ),
        last_error=last_error,
        problem_count=problem_count if last_error is None else max(problem_count, 1),
        counts=counts,
        current_file=current_file,
    )


def build_run_summaries(
    *,
    status: SyncTaskStatus,
    records: list[SyncEventRecord],
) -> list[SyncTaskRunSummaryResponse]:
    records_by_run: dict[str, list[SyncEventRecord]] = {}
    for record in records:
        if not record.run_id:
            continue
        records_by_run.setdefault(record.run_id, []).append(record)
    summaries: list[SyncTaskRunSummaryResponse] = []
    handled_runs: set[str] = set()
    for run_id, run_records in records_by_run.items():
        live_status = status if status.current_run_id == run_id else None
        summaries.append(
            build_run_summary(
                run_id=run_id,
                records=run_records,
                live_status=live_status,
            )
        )
        handled_runs.add(run_id)
    if status.current_run_id and status.current_run_id not in handled_runs:
        summaries.append(
            build_run_summary(
                run_id=status.current_run_id,
                records=[],
                live_status=status,
            )
        )
    summaries.sort(
        key=lambda item: item.last_event_at or item.started_at or item.finished_at or 0.0,
        reverse=True,
    )
    return summaries


def run_summary_from_item(
    item: SyncRunItem,
    *,
    live_status: SyncTaskStatus | None = None,
    records: list[SyncEventRecord] | None = None,
) -> SyncTaskRunSummaryResponse:
    stale_running = item.state == "running" and live_status is None
    display_state = (
        "cancelled" if stale_running else (live_status.state if live_status is not None else item.state)
    )
    display_finished_at = (
        item.finished_at
        if item.finished_at is not None
        else ((item.last_event_at or item.started_at) if stale_running else None)
    )
    display_last_error = (
        live_status.last_error if live_status and live_status.last_error else item.last_error
    )
    if stale_running and not display_last_error:
        display_last_error = "运行被中断，可能是应用退出、更新或进程终止导致"
    current_file = (
        current_file_from_status(live_status)
        if live_status is not None
        else current_file_from_records(records or [])
    )
    counts = SyncTaskDiagnosticCounts(
        total=max(item.total_files, live_status.total_files if live_status else 0),
        processed=max(
            item.completed_files + item.failed_files + item.skipped_files,
            live_status.completed_files + live_status.failed_files + live_status.skipped_files
            if live_status
            else 0,
        ),
        completed=max(item.completed_files, live_status.completed_files if live_status else 0),
        failed=max(item.failed_files, live_status.failed_files if live_status else 0),
        skipped=max(item.skipped_files, live_status.skipped_files if live_status else 0),
        uploaded=max(item.uploaded_files, live_status.uploaded_files if live_status else 0),
        downloaded=max(item.downloaded_files, live_status.downloaded_files if live_status else 0),
        deleted=max(item.deleted_files, live_status.deleted_files if live_status else 0),
        conflicts=max(item.conflict_files, live_status.conflict_files if live_status else 0),
        delete_pending=max(
            item.delete_pending_files,
            live_status.delete_pending_files if live_status else 0,
        ),
        delete_failed=max(
            item.delete_failed_files,
            live_status.delete_failed_files if live_status else 0,
        ),
    )
    problem_count = counts.failed + counts.conflicts + counts.delete_failed
    if display_state == "cancelled":
        problem_count += 1
    return SyncTaskRunSummaryResponse(
        run_id=item.run_id,
        state=display_state,
        run_kind=item.run_kind,
        has_activity=item.has_activity,
        started_at=live_status.started_at if live_status and live_status.started_at is not None else item.started_at,
        finished_at=live_status.finished_at if live_status and live_status.finished_at is not None else display_finished_at,
        last_event_at=(
            records[0].timestamp
            if records
            else (
                live_status.finished_at
                if live_status and live_status.finished_at is not None
                else (
                    live_status.started_at
                    if live_status and live_status.started_at is not None
                    else item.last_event_at
                )
            )
        ),
        last_error=display_last_error,
        problem_count=problem_count if display_last_error is None else max(problem_count, 1),
        counts=counts,
        current_file=current_file,
    )


async def load_run_summaries(
    *,
    task_id: str,
    status: SyncTaskStatus,
    run_service: SyncRunService,
    records: list[SyncEventRecord] | None = None,
) -> list[SyncTaskRunSummaryResponse]:
    db_runs = await run_service.list_by_task(task_id, limit=50)
    if records is None:
        records = []
    records_by_run: dict[str, list[SyncEventRecord]] = {}
    for record in records:
        if record.run_id:
            records_by_run.setdefault(record.run_id, []).append(record)
    if not db_runs:
        if not records and status.current_run_id:
            return [
                build_run_summary(
                    run_id=status.current_run_id,
                    records=[],
                    live_status=status,
                )
            ]
        return build_run_summaries(status=status, records=records)

    summaries: list[SyncTaskRunSummaryResponse] = []
    seen: set[str] = set()
    for item in db_runs:
        live_status = status if status.current_run_id == item.run_id else None
        summaries.append(
            run_summary_from_item(
                item,
                live_status=live_status,
                records=records_by_run.get(item.run_id, []),
            )
        )
        seen.add(item.run_id)
    for run_id, run_records in records_by_run.items():
        if run_id in seen:
            continue
        live_status = status if status.current_run_id == run_id else None
        summaries.append(
            build_run_summary(
                run_id=run_id,
                records=run_records,
                live_status=live_status,
            )
        )
        seen.add(run_id)
    if status.current_run_id and status.current_run_id not in seen:
        summaries.append(
            build_run_summary(
                run_id=status.current_run_id,
                records=[],
                live_status=status,
            )
        )
    summaries.sort(
        key=lambda entry: entry.last_event_at or entry.started_at or entry.finished_at or 0.0,
        reverse=True,
    )
    return summaries


def build_task_overview(
    *,
    task: SyncTaskItem,
    status: SyncTaskStatus,
    records: list[SyncEventRecord],
    run_summaries: list[SyncTaskRunSummaryResponse] | None = None,
    check_state: SyncTaskCheckStateItem | None = None,
) -> SyncTaskOverviewResponse:
    run_summaries = run_summaries or build_run_summaries(status=status, records=records)
    latest_run = run_summaries[0] if run_summaries else None
    processed = max(0, status.completed_files + status.failed_files + status.skipped_files)
    last_result = latest_run.state if latest_run else (
        status.state if status.state in TERMINAL_STATUSES else None
    )
    last_event_at = (
        latest_run.last_event_at
        if latest_run
        else (status.finished_at or status.started_at or task.last_run_at)
    )
    counts = latest_run.counts if latest_run else SyncTaskDiagnosticCounts(
        total=status.total_files,
        processed=processed,
        completed=status.completed_files,
        failed=status.failed_files,
        skipped=status.skipped_files,
    )
    problem_count = latest_run.problem_count if latest_run else (1 if status.last_error else 0)
    return SyncTaskOverviewResponse(
        task=SyncTaskResponse.from_item(task),
        status=SyncTaskStatusResponse.from_status(status),
        last_event_at=last_event_at,
        last_result=last_result,
        problem_count=problem_count,
        counts=counts,
        current_file=latest_run.current_file if latest_run else current_file_from_status(status),
        check_state=(
            SyncTaskCheckStateResponse(
                state=check_state.state,
                trigger_source=check_state.trigger_source,
                started_at=check_state.started_at,
                finished_at=check_state.finished_at,
                last_change_at=check_state.last_change_at,
                change_count=check_state.change_count,
                consecutive_no_change=check_state.consecutive_no_change,
                last_error=check_state.last_error,
            )
            if check_state
            else None
        ),
    )


async def list_task_overviews(
    *,
    items: list[SyncTaskItem],
    statuses: dict[str, SyncTaskStatus],
    run_service: SyncRunService,
    check_state_service: SyncTaskCheckStateService | None = None,
) -> list[SyncTaskOverviewResponse]:
    latest_runs = await run_service.list_latest_by_tasks([item.id for item in items])
    check_states = (
        await check_state_service.get_many([item.id for item in items])
        if check_state_service is not None
        else {}
    )
    results: list[SyncTaskOverviewResponse] = []
    for item in items:
        task_status = statuses.get(item.id) or SyncTaskStatus(task_id=item.id)
        latest_item = latest_runs.get(item.id)
        run_summaries = None
        if latest_item is not None:
            live_status = task_status if task_status.current_run_id == latest_item.run_id else None
            run_summaries = [
                run_summary_from_item(
                    latest_item,
                    live_status=live_status,
                    records=[],
                )
            ]
        results.append(
            build_task_overview(
                task=item,
                status=task_status,
                records=[],
                run_summaries=run_summaries,
                check_state=check_states.get(item.id),
            )
        )
    return results


async def build_task_diagnostics_response(
    *,
    item: SyncTaskItem,
    status: SyncTaskStatus,
    task_id: str,
    limit: int,
    run_id: str,
    include_events: bool,
    include_problems: bool,
    run_service: SyncRunService,
    run_event_service: SyncRunEventService,
    event_store: SyncEventStore,
    check_state: SyncTaskCheckStateItem | None = None,
) -> SyncTaskDiagnosticsResponse:
    run_summaries = await load_run_summaries(
        task_id=task_id,
        status=status,
        run_service=run_service,
        records=None,
    )
    should_scan_history_fallback = bool(run_id.strip()) or include_events or include_problems
    if not run_summaries and item.last_run_at and should_scan_history_fallback:
        _, task_records = await read_sync_events_db_first(
            run_event_service=run_event_service,
            event_store=event_store,
            limit=5000,
            offset=0,
            status="",
            statuses=[],
            search="",
            task_id=task_id,
            task_ids=[],
            run_id="",
            run_ids=[],
            order="desc",
        )
        run_summaries = await load_run_summaries(
            task_id=task_id,
            status=status,
            run_service=run_service,
            records=task_records,
        )
    selected_run = None
    if run_id.strip():
        selected_run = next((entry for entry in run_summaries if entry.run_id == run_id.strip()), None)
    elif run_summaries:
        selected_run = run_summaries[0]
    selected_run_id = selected_run.run_id if selected_run else ""
    selected_run_records: list[SyncEventRecord] = []
    if selected_run_id and (include_events or include_problems):
        scan_limit = max(limit if include_events else 0, 1000 if include_problems else 0, 100)
        _, selected_run_records = await read_sync_events_db_first(
            run_event_service=run_event_service,
            event_store=event_store,
            limit=min(scan_limit, 5000),
            offset=0,
            status="",
            statuses=[],
            search="",
            task_id=task_id,
            task_ids=[],
            run_id=selected_run_id,
            run_ids=[],
            order="desc",
        )
    problem_records = [
        record for record in selected_run_records if record.status in PROBLEM_STATUSES
    ][:100]
    overview = build_task_overview(
        task=item,
        status=status,
        records=selected_run_records if status.current_run_id == selected_run_id else [],
        run_summaries=run_summaries,
        check_state=check_state,
    )
    return SyncTaskDiagnosticsResponse(
        overview=overview,
        selected_run=selected_run,
        recent_runs=run_summaries,
        recent_events=[
            sync_log_entry_from_record(record)
            for record in (selected_run_records[:limit] if include_events else [])
        ],
        problems=[
            sync_log_entry_from_record(record)
            for record in (problem_records if include_problems else [])
        ],
    )


async def build_sync_log_response(
    *,
    limit: int,
    offset: int,
    status: str,
    statuses: list[str],
    search: str,
    task_id: str,
    task_ids: list[str],
    run_id: str,
    run_ids: list[str],
    order: str,
    since: float | None,
    until: float | None,
    retention_days: int,
    warn_size_mb: int,
    event_store: SyncEventStore,
    run_event_service: SyncRunEventService,
) -> SyncLogResponse:
    total, entries = await read_sync_events_db_first(
        run_event_service=run_event_service,
        event_store=event_store,
        limit=limit,
        offset=offset,
        status=status,
        statuses=statuses,
        search=search,
        task_id=task_id,
        task_ids=task_ids,
        run_id=run_id,
        run_ids=run_ids,
        order=order,
        since=since,
        until=until,
    )
    items = [sync_log_entry_from_record(entry) for entry in entries]
    file_size = event_store.file_size_bytes()
    backfill_state = await get_persisted_run_event_backfill_state(
        run_event_service=run_event_service,
        event_store=event_store,
    )
    warning: str | None = None
    if warn_size_mb > 0:
        threshold = warn_size_mb * 1024 * 1024
        if file_size >= threshold:
            size_mb = file_size / (1024 * 1024)
            if retention_days <= 0:
                warning = (
                    f"同步日志已达到 {size_mb:.1f}MB，建议在设置-更多设置中启用保留天数"
                    "（如 90 天）。"
                )
            else:
                warning = f"同步日志已达到 {size_mb:.1f}MB，可调整保留天数或提醒阈值。"
    meta = {
        "file_size_bytes": file_size,
        "retention_days": retention_days,
        "warn_size_mb": warn_size_mb,
        "backfill_status": backfill_state.status if backfill_state else "unknown",
        "backfill_completed": backfill_state.completed if backfill_state else False,
        "backfill_offset": backfill_state.offset if backfill_state else 0,
        "backfill_file_size": backfill_state.log_size if backfill_state else file_size,
    }
    return SyncLogResponse(total=total, items=items, warning=warning, meta=meta)
