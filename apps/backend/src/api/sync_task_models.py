from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.core.config import DeletePolicy, SyncMode
from src.services.sync_runner import SyncFileEvent, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


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
    ignored_subpaths: list[str] | None = Field(
        default=None,
        description="忽略的本地子目录列表",
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
    ignored_subpaths: list[str] | None = None
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
    ignored_subpaths: list[str]
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


class SyncTaskFolderResponse(BaseModel):
    path: str


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
    uploaded_files: int = 0
    downloaded_files: int = 0
    deleted_files: int = 0
    conflict_files: int = 0
    delete_pending_files: int = 0
    delete_failed_files: int = 0
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
            uploaded_files=status.uploaded_files,
            downloaded_files=status.downloaded_files,
            deleted_files=status.deleted_files,
            conflict_files=status.conflict_files,
            delete_pending_files=status.delete_pending_files,
            delete_failed_files=status.delete_failed_files,
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
    event_id: str | None = None
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
