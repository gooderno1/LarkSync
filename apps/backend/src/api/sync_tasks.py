from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.config import ConfigManager, DeletePolicy, SyncMode
from src.core.logging import get_log_file
from src.services.docx_service import DocxService, DocxServiceError
from src.services.log_reader import prune_log_file, read_log_entries
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_link_service import SyncLinkService
from src.services.sync_run_service import SyncRunItem, SyncRunService
from src.services.sync_runner import SyncFileEvent, SyncTaskRunner, SyncTaskStatus
from src.services.sync_task_service import (
    SyncTaskItem,
    SyncTaskService,
    SyncTaskValidationError,
)
from src.services.sync_tombstone_service import SyncTombstoneService


class SyncTaskCreateRequest(BaseModel):
    name: str | None = Field(default=None, description="任务名称")
    local_path: str = Field(..., description="本地同步根目录")
    cloud_folder_token: str = Field(..., description="云端文件夹 token")
    cloud_folder_name: str | None = Field(default=None, description="云端文件夹显示名称/路径")
    base_path: str | None = Field(default=None, description="Markdown 基准路径")
    sync_mode: SyncMode = Field(default=SyncMode.bidirectional, description="同步模式")
    update_mode: Literal["auto", "partial", "full"] = Field(
        default="auto", description="更新模式"
    )
    md_sync_mode: Literal["enhanced", "download_only", "doc_only"] = Field(
        default="enhanced", description="Markdown 上传模式"
    )
    delete_policy: DeletePolicy | None = Field(default=None, description="删除联动策略")
    delete_grace_minutes: int | None = Field(default=None, ge=0, description="删除宽限分钟")
    is_test: bool = Field(default=False, description="是否测试任务")
    enabled: bool = Field(default=True, description="是否启用")


class SyncTaskUpdateRequest(BaseModel):
    name: str | None = None
    local_path: str | None = None
    cloud_folder_token: str | None = None
    cloud_folder_name: str | None = None
    base_path: str | None = None
    sync_mode: SyncMode | None = None
    update_mode: Literal["auto", "partial", "full"] | None = None
    md_sync_mode: Literal["enhanced", "download_only", "doc_only"] | None = None
    delete_policy: DeletePolicy | None = None
    delete_grace_minutes: int | None = Field(default=None, ge=0)
    is_test: bool | None = None
    enabled: bool | None = None


class SyncTaskResponse(BaseModel):
    id: str
    name: str | None
    local_path: str
    cloud_folder_token: str
    cloud_folder_name: str | None
    base_path: str | None
    sync_mode: str
    update_mode: str
    md_sync_mode: str
    delete_policy: str | None
    delete_grace_minutes: int | None
    is_test: bool
    enabled: bool
    created_at: float
    updated_at: float
    last_run_at: float | None = None

    @classmethod
    def from_item(cls, item: SyncTaskItem) -> "SyncTaskResponse":
        return cls(**item.__dict__)


class MarkdownReplaceRequest(BaseModel):
    document_id: str = Field(..., description="文档 token")
    markdown_path: str = Field(..., description="Markdown 文件路径")
    task_id: str | None = Field(default=None, description="可选任务 ID，用于推导 base_path")
    base_path: str | None = Field(default=None, description="可选 Markdown 基准路径")
    update_mode: Literal["auto", "full", "partial"] = Field(
        default="auto", description="更新模式"
    )
    user_id_type: Literal["open_id", "union_id", "user_id"] = Field(
        default="open_id", description="用户 ID 类型"
    )


router = APIRouter(prefix="/sync", tags=["sync"])
service = SyncTaskService()
runner = SyncTaskRunner(task_service=service)
event_store = SyncEventStore()
run_service = SyncRunService()
_PROBLEM_STATUSES = {"failed", "delete_failed", "conflict", "cancelled"}
_TERMINAL_STATUSES = {"success", "failed", "cancelled"}
_CURRENT_FILE_EXCLUDED_STATUSES = {"started", "success", "failed", "cancelled"}


class SyncFileEventResponse(BaseModel):
    path: str
    status: str
    message: str | None = None
    timestamp: float

    @classmethod
    def from_event(cls, event: SyncFileEvent) -> "SyncFileEventResponse":
        return cls(
            path=event.path,
            status=event.status,
            message=event.message,
            timestamp=event.timestamp,
        )


class SyncTaskStatusResponse(BaseModel):
    task_id: str
    state: str
    started_at: float | None = None
    finished_at: float | None = None
    total_files: int
    completed_files: int
    failed_files: int
    skipped_files: int
    last_error: str | None = None
    current_run_id: str | None = None
    last_files: list[SyncFileEventResponse] = Field(default_factory=list)

    @classmethod
    def from_status(cls, status: SyncTaskStatus) -> "SyncTaskStatusResponse":
        return cls(
            task_id=status.task_id,
            state=status.state,
            started_at=status.started_at,
            finished_at=status.finished_at,
            total_files=status.total_files,
            completed_files=status.completed_files,
            failed_files=status.failed_files,
            skipped_files=status.skipped_files,
            last_error=status.last_error,
            current_run_id=status.current_run_id,
            last_files=[SyncFileEventResponse.from_event(evt) for evt in status.last_files],
        )


class SyncTaskDiagnosticCounts(BaseModel):
    total: int = 0
    processed: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    uploaded: int = 0
    downloaded: int = 0
    deleted: int = 0
    conflicts: int = 0
    delete_pending: int = 0
    delete_failed: int = 0


class SyncTaskOverviewResponse(BaseModel):
    task: SyncTaskResponse
    status: SyncTaskStatusResponse
    last_event_at: float | None = None
    last_result: str | None = None
    problem_count: int = 0
    counts: SyncTaskDiagnosticCounts
    current_file: SyncFileEventResponse | None = None


class SyncLogEntry(BaseModel):
    task_id: str
    task_name: str
    timestamp: float
    status: str
    path: str
    message: str | None = None
    run_id: str | None = None


class SyncTaskRunSummaryResponse(BaseModel):
    run_id: str
    state: str
    started_at: float | None = None
    finished_at: float | None = None
    last_event_at: float | None = None
    last_error: str | None = None
    problem_count: int = 0
    counts: SyncTaskDiagnosticCounts
    current_file: SyncFileEventResponse | None = None


class SyncTaskDiagnosticsResponse(BaseModel):
    overview: SyncTaskOverviewResponse
    selected_run: SyncTaskRunSummaryResponse | None = None
    recent_runs: list[SyncTaskRunSummaryResponse] = Field(default_factory=list)
    recent_events: list[SyncLogEntry] = Field(default_factory=list)
    problems: list[SyncLogEntry] = Field(default_factory=list)


def _sync_log_entry_from_record(record: SyncEventRecord) -> SyncLogEntry:
    return SyncLogEntry(
        task_id=record.task_id,
        task_name=record.task_name,
        timestamp=record.timestamp,
        status=record.status,
        path=record.path,
        message=record.message,
        run_id=record.run_id,
    )


def _current_file_from_status(status: SyncTaskStatus) -> SyncFileEventResponse | None:
    for event in reversed(status.last_files):
        if event.status not in _CURRENT_FILE_EXCLUDED_STATUSES:
            return SyncFileEventResponse.from_event(event)
    return None


def _file_event_from_record(record: SyncEventRecord) -> SyncFileEventResponse:
    return SyncFileEventResponse(
        path=record.path,
        status=record.status,
        message=record.message,
        timestamp=record.timestamp,
    )


def _current_file_from_records(records: list[SyncEventRecord]) -> SyncFileEventResponse | None:
    for record in records:
        if record.status not in _CURRENT_FILE_EXCLUDED_STATUSES:
            return _file_event_from_record(record)
    return None


def _build_run_counts(
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


def _derive_run_state(records: list[SyncEventRecord], live_status: SyncTaskStatus | None) -> str:
    if live_status is not None:
        return live_status.state
    for record in records:
        if record.status in _TERMINAL_STATUSES:
            return record.status
    if any(record.status in _PROBLEM_STATUSES for record in records):
        return "failed"
    if records:
        return "success"
    return "idle"


def _build_run_summary(
    *,
    run_id: str,
    records: list[SyncEventRecord],
    live_status: SyncTaskStatus | None = None,
) -> SyncTaskRunSummaryResponse:
    ordered_records = sorted(records, key=lambda item: item.timestamp, reverse=True)
    event_counts: dict[str, int] = {}
    for record in ordered_records:
        event_counts[record.status] = event_counts.get(record.status, 0) + 1
    started_record = next((record for record in reversed(ordered_records) if record.status == "started"), None)
    finished_record = next((record for record in ordered_records if record.status in _TERMINAL_STATUSES), None)
    last_problem = next((record for record in ordered_records if record.status in _PROBLEM_STATUSES), None)
    counts = _build_run_counts(event_counts=event_counts, status=live_status)
    state = _derive_run_state(ordered_records, live_status)
    started_at = (
        live_status.started_at
        if live_status and live_status.started_at is not None
        else (started_record.timestamp if started_record else (ordered_records[-1].timestamp if ordered_records else None))
    )
    finished_at = (
        live_status.finished_at
        if live_status and live_status.finished_at is not None
        else (finished_record.timestamp if finished_record else (None if state == "running" else (ordered_records[0].timestamp if ordered_records else None)))
    )
    current_file = (
        _current_file_from_status(live_status)
        if live_status is not None
        else _current_file_from_records(ordered_records)
    )
    problem_count = sum(
        count for event_status, count in event_counts.items()
        if event_status in _PROBLEM_STATUSES
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


def _build_run_summaries(
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
            _build_run_summary(
                run_id=run_id,
                records=run_records,
                live_status=live_status,
            )
        )
        handled_runs.add(run_id)
    if status.current_run_id and status.current_run_id not in handled_runs:
        summaries.append(
            _build_run_summary(
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


def _run_summary_from_item(
    item: SyncRunItem,
    *,
    live_status: SyncTaskStatus | None = None,
    records: list[SyncEventRecord] | None = None,
) -> SyncTaskRunSummaryResponse:
    stale_running = item.state == "running" and live_status is None
    display_state = "cancelled" if stale_running else (
        live_status.state if live_status is not None else item.state
    )
    display_finished_at = (
        item.finished_at
        if item.finished_at is not None
        else ((item.last_event_at or item.started_at) if stale_running else None)
    )
    display_last_error = (
        live_status.last_error
        if live_status and live_status.last_error
        else item.last_error
    )
    if stale_running and not display_last_error:
        display_last_error = "运行被中断，可能是应用退出、更新或进程终止导致"
    current_file = (
        _current_file_from_status(live_status)
        if live_status is not None
        else _current_file_from_records(records or [])
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


async def _load_run_summaries(
    *,
    task_id: str,
    status: SyncTaskStatus,
    records: list[SyncEventRecord],
) -> list[SyncTaskRunSummaryResponse]:
    records_by_run: dict[str, list[SyncEventRecord]] = {}
    for record in records:
        if record.run_id:
            records_by_run.setdefault(record.run_id, []).append(record)
    db_runs = await run_service.list_by_task(task_id, limit=50)
    if not db_runs:
        return _build_run_summaries(status=status, records=records)
    summaries: list[SyncTaskRunSummaryResponse] = []
    seen: set[str] = set()
    for item in db_runs:
        live_status = status if status.current_run_id == item.run_id else None
        summaries.append(
            _run_summary_from_item(
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
            _build_run_summary(
                run_id=run_id,
                records=run_records,
                live_status=live_status,
            )
        )
        seen.add(run_id)
    if status.current_run_id and status.current_run_id not in seen:
        summaries.append(
            _build_run_summary(
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


def _build_task_overview(
    *,
    task: SyncTaskItem,
    status: SyncTaskStatus,
    records: list[SyncEventRecord],
    run_summaries: list[SyncTaskRunSummaryResponse] | None = None,
) -> SyncTaskOverviewResponse:
    run_summaries = run_summaries or _build_run_summaries(status=status, records=records)
    latest_run = run_summaries[0] if run_summaries else None
    processed = max(0, status.completed_files + status.failed_files + status.skipped_files)
    last_result = latest_run.state if latest_run else (
        status.state if status.state in _TERMINAL_STATUSES else None
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
        current_file=latest_run.current_file if latest_run else _current_file_from_status(status),
    )


@router.get("/tasks", response_model=list[SyncTaskResponse])
async def list_tasks() -> list[SyncTaskResponse]:
    items = await service.list_tasks()
    return [SyncTaskResponse.from_item(item) for item in items]


@router.get("/tasks/status", response_model=list[SyncTaskStatusResponse])
async def list_task_status() -> list[SyncTaskStatusResponse]:
    statuses = runner.list_statuses()
    return [SyncTaskStatusResponse.from_status(status) for status in statuses.values()]


@router.get("/tasks/overview", response_model=list[SyncTaskOverviewResponse])
async def list_task_overview() -> list[SyncTaskOverviewResponse]:
    items = await service.list_tasks()
    statuses = runner.list_statuses()
    _, recent_records = event_store.read_events(
        limit=2000,
        offset=0,
        status="",
        search="",
        task_id="",
        order="desc",
    )
    records_by_task: dict[str, list[SyncEventRecord]] = {}
    for record in recent_records:
        records_by_task.setdefault(record.task_id, []).append(record)
    latest_runs = await run_service.list_latest_by_tasks([item.id for item in items])
    results: list[SyncTaskOverviewResponse] = []
    for item in items:
        task_status = statuses.get(item.id) or SyncTaskStatus(task_id=item.id)
        task_records = records_by_task.get(item.id, [])
        latest_item = latest_runs.get(item.id)
        run_summaries = None
        if latest_item is not None:
            live_status = task_status if task_status.current_run_id == latest_item.run_id else None
            run_records = [record for record in task_records if record.run_id == latest_item.run_id]
            run_summaries = [
                _run_summary_from_item(
                    latest_item,
                    live_status=live_status,
                    records=run_records,
                )
            ]
        results.append(
            _build_task_overview(
                task=item,
                status=task_status,
                records=task_records,
                run_summaries=run_summaries,
            )
        )
    return results


@router.get("/tasks/{task_id}/diagnostics", response_model=SyncTaskDiagnosticsResponse)
async def get_task_diagnostics(
    task_id: str,
    limit: int = Query(default=200, ge=1, le=1000, description="返回事件条数"),
    run_id: str = Query(default="", description="指定运行 ID，仅返回该次运行数据"),
) -> SyncTaskDiagnosticsResponse:
    item = await service.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    status = runner.get_status(task_id)
    _, task_records = event_store.read_events(
        limit=5000,
        offset=0,
        status="",
        search="",
        task_id=task_id,
        order="desc",
    )
    run_summaries = await _load_run_summaries(
        task_id=task_id,
        status=status,
        records=task_records,
    )
    selected_run = None
    if run_id.strip():
        selected_run = next((item for item in run_summaries if item.run_id == run_id.strip()), None)
    elif run_summaries:
        selected_run = run_summaries[0]
    selected_run_id = selected_run.run_id if selected_run else ""
    _, recent_records = event_store.read_events(
        limit=limit,
        offset=0,
        status="",
        search="",
        task_id=task_id,
        run_id=selected_run_id,
        order="desc",
    )
    _, problem_records = event_store.read_events(
        limit=100,
        offset=0,
        status="",
        statuses=sorted(_PROBLEM_STATUSES),
        search="",
        task_id=task_id,
        run_id=selected_run_id,
        order="desc",
    )
    overview = _build_task_overview(
        task=item,
        status=status,
        records=task_records,
        run_summaries=run_summaries,
    )
    return SyncTaskDiagnosticsResponse(
        overview=overview,
        selected_run=selected_run,
        recent_runs=run_summaries,
        recent_events=[_sync_log_entry_from_record(record) for record in recent_records],
        problems=[_sync_log_entry_from_record(record) for record in problem_records],
    )


@router.post("/tasks", response_model=SyncTaskResponse)
async def create_task(payload: SyncTaskCreateRequest) -> SyncTaskResponse:
    try:
        item = await service.create_task(
            name=payload.name,
            local_path=payload.local_path,
            cloud_folder_token=payload.cloud_folder_token,
            cloud_folder_name=payload.cloud_folder_name,
            base_path=payload.base_path,
            sync_mode=payload.sync_mode.value,
            update_mode=payload.update_mode,
            md_sync_mode=payload.md_sync_mode,
            delete_policy=payload.delete_policy.value if payload.delete_policy else None,
            delete_grace_minutes=payload.delete_grace_minutes,
            is_test=payload.is_test,
            enabled=payload.enabled,
        )
    except SyncTaskValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item.enabled:
        runner.start_task(item)
    return SyncTaskResponse.from_item(item)


@router.patch("/tasks/{task_id}", response_model=SyncTaskResponse)
async def update_task(task_id: str, payload: SyncTaskUpdateRequest) -> SyncTaskResponse:
    try:
        item = await service.update_task(
            task_id,
            name=payload.name,
            local_path=payload.local_path,
            cloud_folder_token=payload.cloud_folder_token,
            cloud_folder_name=payload.cloud_folder_name,
            base_path=payload.base_path,
            sync_mode=payload.sync_mode.value if payload.sync_mode else None,
            update_mode=payload.update_mode,
            md_sync_mode=payload.md_sync_mode,
            delete_policy=payload.delete_policy.value if payload.delete_policy else None,
            delete_grace_minutes=payload.delete_grace_minutes,
            is_test=payload.is_test,
            enabled=payload.enabled,
        )
    except SyncTaskValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.enabled is False:
        runner.cancel_task(task_id)
    if payload.sync_mode is not None:
        runner.cancel_task(task_id)
    if item.enabled:
        runner.start_task(item)
    return SyncTaskResponse.from_item(item)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict:
    runner.cancel_task(task_id)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    link_service = SyncLinkService()
    tombstone_service = SyncTombstoneService()
    await link_service.delete_by_task(task_id)
    await tombstone_service.delete_by_task(task_id)
    return {"status": "deleted"}


@router.post("/tasks/{task_id}/reset-links")
async def reset_task_links(task_id: str) -> dict:
    """清除指定任务的所有同步映射（SyncLink），用于修复上传位置错误等问题。

    清除后下一次同步会重新建立映射关系。
    """
    item = await service.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    link_service = SyncLinkService()
    tombstone_service = SyncTombstoneService()
    count = await link_service.delete_by_task(task_id)
    await tombstone_service.delete_by_task(task_id)
    # 同时清除初始扫描标记，确保下次上传调度重新扫描
    runner._initial_upload_scanned.discard(task_id)
    runner._cloud_folder_cache = {
        k: v for k, v in runner._cloud_folder_cache.items() if k[0] != task_id
    }
    return {"status": "ok", "deleted_links": count}


@router.post("/tasks/{task_id}/run", response_model=SyncTaskStatusResponse)
async def run_task(task_id: str) -> SyncTaskStatusResponse:
    item = await service.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    status = runner.start_task(item)
    return SyncTaskStatusResponse.from_status(status)


@router.get("/tasks/{task_id}/status", response_model=SyncTaskStatusResponse)
async def get_task_status(task_id: str) -> SyncTaskStatusResponse:
    status = runner.get_status(task_id)
    return SyncTaskStatusResponse.from_status(status)


@router.post("/markdown/replace")
async def replace_markdown(payload: MarkdownReplaceRequest) -> dict:
    path = Path(payload.markdown_path).expanduser()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=400, detail="Markdown 路径无效")

    base_path = payload.base_path
    if not base_path and payload.task_id:
        task = await service.get_task(payload.task_id)
        if task:
            base_path = task.base_path or task.local_path
    if not base_path:
        base_path = path.parent.as_posix()

    markdown = path.read_text(encoding="utf-8")
    docx_service = DocxService()
    try:
        await docx_service.replace_document_content(
            payload.document_id,
            markdown,
            user_id_type=payload.user_id_type,
            base_path=base_path,
            update_mode=payload.update_mode,
        )
    except DocxServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await docx_service.close()
    return {"status": "ok"}


class LogFileEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class LogFileResponse(BaseModel):
    total: int
    items: list[LogFileEntry]


class SyncLogResponse(BaseModel):
    total: int
    items: list[SyncLogEntry]
    warning: str | None = None
    meta: dict[str, object] | None = None


@router.get("/logs/sync", response_model=SyncLogResponse)
async def read_sync_logs(
    limit: int = Query(default=50, ge=1, le=2000, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="跳过前N条"),
    status: str = Query(default="", description="按状态筛选"),
    statuses: list[str] = Query(default_factory=list, description="按状态筛选（可多选）"),
    search: str = Query(default="", description="关键词搜索"),
    task_id: str = Query(default="", description="任务 ID 过滤"),
    task_ids: list[str] = Query(default_factory=list, description="任务 ID 多选过滤"),
    run_id: str = Query(default="", description="运行 ID 过滤"),
    run_ids: list[str] = Query(default_factory=list, description="运行 ID 多选过滤"),
    order: str = Query(default="desc", description="排序: desc=最新优先, asc=最早优先"),
) -> SyncLogResponse:
    """读取同步日志（持久化 JSONL）。"""
    config = ConfigManager.get().config
    retention_days = int(config.sync_log_retention_days or 0)
    warn_size_mb = int(config.sync_log_warn_size_mb or 0)
    if retention_days > 0:
        event_store.prune(retention_days=retention_days, min_interval_seconds=120)
    total, entries = event_store.read_events(
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
    )
    items = [_sync_log_entry_from_record(entry) for entry in entries]
    file_size = event_store.file_size_bytes()
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
                warning = (
                    f"同步日志已达到 {size_mb:.1f}MB，可调整保留天数或提醒阈值。"
                )
    meta = {
        "file_size_bytes": file_size,
        "retention_days": retention_days,
        "warn_size_mb": warn_size_mb,
    }
    return SyncLogResponse(total=total, items=items, warning=warning, meta=meta)


@router.get("/logs/file", response_model=LogFileResponse)
async def read_log_file(
    limit: int = Query(default=50, ge=1, le=2000, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="跳过前N条"),
    level: str = Query(default="", description="按级别筛选 (INFO/WARNING/ERROR)"),
    search: str = Query(default="", description="关键词搜索"),
    order: str = Query(default="desc", description="排序: desc=最新优先, asc=最早优先"),
) -> LogFileResponse:
    """读取 loguru 日志文件，支持分页返回最近的日志条目。"""
    log_file = get_log_file()
    if not log_file.exists():
        return LogFileResponse(total=0, items=[])
    config = ConfigManager.get().config
    retention_days = int(config.system_log_retention_days or 1)
    if retention_days <= 0:
        retention_days = 1
    prune_log_file(log_file, retention_days=retention_days, min_interval_seconds=120)
    total, entries = read_log_entries(
        log_file,
        limit=limit,
        offset=offset,
        level=level,
        search=search,
        order=order,
    )
    items = [
        LogFileEntry(timestamp=ts, level=lvl, message=msg)
        for ts, lvl, msg in entries
    ]
    return LogFileResponse(total=total, items=items)
