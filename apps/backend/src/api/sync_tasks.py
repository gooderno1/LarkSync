from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.config import SyncMode
from src.services.docx_service import DocxService, DocxServiceError
from src.services.sync_runner import SyncFileEvent, SyncTaskRunner, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem, SyncTaskService


class SyncTaskCreateRequest(BaseModel):
    name: str | None = Field(default=None, description="任务名称")
    local_path: str = Field(..., description="本地同步根目录")
    cloud_folder_token: str = Field(..., description="云端文件夹 token")
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
    base_path: str | None = None
    sync_mode: SyncMode | None = None
    update_mode: Literal["auto", "partial", "full"] | None = None
    enabled: bool | None = None


class SyncTaskResponse(BaseModel):
    id: str
    name: str | None
    local_path: str
    cloud_folder_token: str
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


class SyncFileEventResponse(BaseModel):
    path: str
    status: str
    message: str | None = None

    @classmethod
    def from_event(cls, event: SyncFileEvent) -> "SyncFileEventResponse":
        return cls(path=event.path, status=event.status, message=event.message)


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
