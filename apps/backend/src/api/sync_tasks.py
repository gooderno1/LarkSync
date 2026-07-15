from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from src.api.sync_task_models import (
    LogFileEntry,
    LogFileResponse,
    MarkdownReplaceRequest,
    SyncLogResponse,
    SyncTaskCreateRequest,
    SyncTaskDiagnosticsResponse,
    SyncTaskFolderResponse,
    SyncTaskOverviewResponse,
    SyncTaskResponse,
    SyncTaskStatusResponse,
    SyncTaskUpdateRequest,
)
from src.core.config import ConfigManager
from src.core.file_manager import open_directory_in_file_manager as _open_directory_in_file_manager
from src.core.logging import get_log_file
from src.core.runtime_safety import validate_task_runtime
from src.services.docx_service import DocxService, DocxServiceError
from src.services.log_reader import prune_log_file, read_log_entries
from src.services.sync_event_store import SyncEventStore
from src.services.sync_task_diagnostics_service import (
    build_sync_log_response,
    build_task_diagnostics_response,
    list_task_overviews,
)
from src.services.sync_link_service import SyncLinkService
from src.services.sync_run_event_service import SyncRunEventService
from src.services.sync_run_service import SyncRunItem, SyncRunService
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import (
    SyncTaskItem,
    SyncTaskService,
    SyncTaskValidationError,
)
from src.services.sync_tombstone_service import SyncTombstoneService

router = APIRouter(prefix="/sync", tags=["sync"])
service = SyncTaskService()
runner = SyncTaskRunner(task_service=service)
event_store = SyncEventStore()
run_event_service = SyncRunEventService()
run_service = SyncRunService()


def _enforce_task_runtime(
    *,
    sync_mode: str,
    cloud_folder_token: str,
    delete_policy: str | None,
) -> None:
    issues = validate_task_runtime(
        ConfigManager.get().config,
        sync_mode=sync_mode,
        cloud_folder_token=cloud_folder_token,
        delete_policy=delete_policy,
    )
    if issues:
        raise HTTPException(status_code=403, detail="；".join(issues))

def _task_update_requires_restart(payload: SyncTaskUpdateRequest) -> bool:
    return any(
        value is not None
        for value in (
            payload.local_path,
            payload.cloud_folder_token,
            payload.cloud_folder_name,
            payload.base_path,
            payload.sync_mode,
            payload.update_mode,
            payload.md_sync_mode,
            payload.ignored_subpaths,
            payload.delete_policy,
            payload.delete_grace_minutes,
        )
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
    return await list_task_overviews(
        items=items,
        statuses=runner.list_statuses(),
        run_service=run_service,
    )


@router.get("/tasks/{task_id}/diagnostics", response_model=SyncTaskDiagnosticsResponse)
async def get_task_diagnostics(
    task_id: str,
    limit: int = Query(default=200, ge=1, le=1000, description="返回事件条数"),
    run_id: str = Query(default="", description="指定运行 ID，仅返回该次运行数据"),
    include_events: bool = Query(default=True, description="是否返回 recent_events"),
    include_problems: bool = Query(default=True, description="是否返回 problems"),
) -> SyncTaskDiagnosticsResponse:
    item = await service.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    return await build_task_diagnostics_response(
        item=item,
        status=runner.get_status(task_id),
        task_id=task_id,
        limit=limit,
        run_id=run_id,
        include_events=include_events,
        include_problems=include_problems,
        run_service=run_service,
        run_event_service=run_event_service,
        event_store=event_store,
    )


@router.post("/tasks/{task_id}/open-local-folder", response_model=SyncTaskFolderResponse)
async def open_task_local_folder(task_id: str) -> SyncTaskFolderResponse:
    item = await service.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    folder = Path(item.local_path)
    try:
        _open_directory_in_file_manager(folder)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"打开目录失败: {exc}") from exc
    return SyncTaskFolderResponse(path=item.local_path)


@router.post("/tasks", response_model=SyncTaskResponse)
async def create_task(payload: SyncTaskCreateRequest) -> SyncTaskResponse:
    config = ConfigManager.get().config
    _enforce_task_runtime(
        sync_mode=payload.sync_mode.value,
        cloud_folder_token=payload.cloud_folder_token,
        delete_policy=(
            payload.delete_policy.value
            if payload.delete_policy
            else config.delete_policy.value
        ),
    )
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
        ignored_subpaths=payload.ignored_subpaths,
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
    should_restart = _task_update_requires_restart(payload)
    current = await service.get_task(task_id)
    if not current:
        raise HTTPException(status_code=404, detail="Task not found")
    config = ConfigManager.get().config
    _enforce_task_runtime(
        sync_mode=payload.sync_mode.value if payload.sync_mode else current.sync_mode,
        cloud_folder_token=payload.cloud_folder_token or current.cloud_folder_token,
        delete_policy=(
            payload.delete_policy.value
            if payload.delete_policy
            else current.delete_policy or config.delete_policy.value
        ),
    )
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
        ignored_subpaths=payload.ignored_subpaths,
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
    elif item.enabled and should_restart:
        runner.restart_task(item, reason="任务配置已更新，正在应用新配置")
    elif item.enabled:
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
    config = ConfigManager.get().config
    _enforce_task_runtime(
        sync_mode=item.sync_mode,
        cloud_folder_token=item.cloud_folder_token,
        delete_policy=item.delete_policy or config.delete_policy.value,
    )
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
    return await build_sync_log_response(
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
        retention_days=int(config.sync_log_retention_days or 0),
        warn_size_mb=int(config.sync_log_warn_size_mb or 0),
        event_store=event_store,
        run_event_service=run_event_service,
    )


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
