from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.config import ConfigManager, SyncMode
from src.core.logging import get_log_file
from src.services.docx_service import DocxService, DocxServiceError
from src.services.log_reader import prune_log_file, read_log_entries
from src.services.sync_event_store import SyncEventStore
from src.services.sync_link_service import SyncLinkService
from src.services.sync_runner import SyncFileEvent, SyncTaskRunner, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem, SyncTaskService


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
    enabled: bool = Field(default=True, description="是否启用")


class SyncTaskUpdateRequest(BaseModel):
    name: str | None = None
    local_path: str | None = None
    cloud_folder_token: str | None = None
    cloud_folder_name: str | None = None
    base_path: str | None = None
    sync_mode: SyncMode | None = None
    update_mode: Literal["auto", "partial", "full"] | None = None
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
    enabled: bool
    created_at: float
    updated_at: float

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
runner = SyncTaskRunner()
event_store = SyncEventStore()


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
            last_files=[SyncFileEventResponse.from_event(evt) for evt in status.last_files],
        )


@router.get("/tasks", response_model=list[SyncTaskResponse])
async def list_tasks() -> list[SyncTaskResponse]:
    items = await service.list_tasks()
    return [SyncTaskResponse.from_item(item) for item in items]


@router.get("/tasks/status", response_model=list[SyncTaskStatusResponse])
async def list_task_status() -> list[SyncTaskStatusResponse]:
    statuses = runner.list_statuses()
    return [SyncTaskStatusResponse.from_status(status) for status in statuses.values()]


@router.post("/tasks", response_model=SyncTaskResponse)
async def create_task(payload: SyncTaskCreateRequest) -> SyncTaskResponse:
    item = await service.create_task(
        name=payload.name,
        local_path=payload.local_path,
        cloud_folder_token=payload.cloud_folder_token,
        cloud_folder_name=payload.cloud_folder_name,
        base_path=payload.base_path,
        sync_mode=payload.sync_mode.value,
        update_mode=payload.update_mode,
        enabled=payload.enabled,
    )
    if item.enabled:
        runner.start_task(item)
    return SyncTaskResponse.from_item(item)


@router.patch("/tasks/{task_id}", response_model=SyncTaskResponse)
async def update_task(task_id: str, payload: SyncTaskUpdateRequest) -> SyncTaskResponse:
    item = await service.update_task(
        task_id,
        name=payload.name,
        local_path=payload.local_path,
        cloud_folder_token=payload.cloud_folder_token,
        cloud_folder_name=payload.cloud_folder_name,
        base_path=payload.base_path,
        sync_mode=payload.sync_mode.value if payload.sync_mode else None,
        update_mode=payload.update_mode,
        enabled=payload.enabled,
    )
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
    count = await link_service.delete_by_task(task_id)
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


class SyncLogEntry(BaseModel):
    task_id: str
    task_name: str
    timestamp: float
    status: str
    path: str
    message: str | None = None


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
    search: str = Query(default="", description="关键词搜索"),
    task_id: str = Query(default="", description="任务 ID 过滤"),
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
        search=search,
        task_id=task_id,
        order=order,
    )
    items = [
        SyncLogEntry(
            task_id=entry.task_id,
            task_name=entry.task_name,
            timestamp=entry.timestamp,
            status=entry.status,
            path=entry.path,
            message=entry.message,
        )
        for entry in entries
    ]
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
