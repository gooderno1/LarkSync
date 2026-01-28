from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.config import SyncMode
from src.services.docx_service import DocxService, DocxServiceError
from src.services.sync_task_service import SyncTaskItem, SyncTaskService


class SyncTaskCreateRequest(BaseModel):
    name: str | None = Field(default=None, description="任务名称")
    local_path: str = Field(..., description="本地同步根目录")
    cloud_folder_token: str = Field(..., description="云端文件夹 token")
    base_path: str | None = Field(default=None, description="Markdown 基准路径")
    sync_mode: SyncMode = Field(default=SyncMode.bidirectional, description="同步模式")
    enabled: bool = Field(default=True, description="是否启用")


class SyncTaskUpdateRequest(BaseModel):
    name: str | None = None
    local_path: str | None = None
    cloud_folder_token: str | None = None
    base_path: str | None = None
    sync_mode: SyncMode | None = None
    enabled: bool | None = None


class SyncTaskResponse(BaseModel):
    id: str
    name: str | None
    local_path: str
    cloud_folder_token: str
    base_path: str | None
    sync_mode: str
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
    user_id_type: Literal["open_id", "union_id", "user_id"] = Field(
        default="open_id", description="用户 ID 类型"
    )


router = APIRouter(prefix="/sync", tags=["sync"])
service = SyncTaskService()


@router.get("/tasks", response_model=list[SyncTaskResponse])
async def list_tasks() -> list[SyncTaskResponse]:
    items = await service.list_tasks()
    return [SyncTaskResponse.from_item(item) for item in items]


@router.post("/tasks", response_model=SyncTaskResponse)
async def create_task(payload: SyncTaskCreateRequest) -> SyncTaskResponse:
    item = await service.create_task(
        name=payload.name,
        local_path=payload.local_path,
        cloud_folder_token=payload.cloud_folder_token,
        base_path=payload.base_path,
        sync_mode=payload.sync_mode.value,
        enabled=payload.enabled,
    )
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
        enabled=payload.enabled,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    return SyncTaskResponse.from_item(item)


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
        )
    except DocxServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await docx_service.close()
    return {"status": "ok"}
