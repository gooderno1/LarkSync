from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.conflict_service import ConflictItem, ConflictService


class ConflictCreateRequest(BaseModel):
    local_path: str = Field(..., description="本地文件路径")
    cloud_token: str = Field(..., description="云端文件 token")
    local_hash: str = Field(..., description="本地文件 hash")
    db_hash: str = Field(..., description="DB 记录 hash")
    cloud_version: int = Field(..., description="云端版本号")
    db_version: int = Field(..., description="DB 版本号")
    local_preview: str | None = Field(default=None, description="本地预览文本")
    cloud_preview: str | None = Field(default=None, description="云端预览文本")


class ConflictResolveRequest(BaseModel):
    action: Literal["use_local", "use_cloud"] = Field(..., description="解决策略")


class ConflictCheckResponse(BaseModel):
    conflict: bool
    item: "ConflictResponse | None" = None


class ConflictResponse(BaseModel):
    id: str
    local_path: str
    cloud_token: str
    local_hash: str
    db_hash: str
    cloud_version: int
    db_version: int
    local_preview: str | None
    cloud_preview: str | None
    created_at: float
    resolved: bool
    resolved_action: str | None

    @classmethod
    def from_item(cls, item: ConflictItem) -> "ConflictResponse":
        return cls(**item.__dict__)


router = APIRouter(prefix="/conflicts", tags=["conflicts"])
service = ConflictService()


@router.get("")
async def list_conflicts(include_resolved: bool = False) -> list[ConflictResponse]:
    return [ConflictResponse.from_item(item) for item in service.list_conflicts(include_resolved)]


@router.post("", response_model=ConflictResponse)
async def create_conflict(payload: ConflictCreateRequest) -> ConflictResponse:
    item = service.add_conflict(**payload.model_dump())
    return ConflictResponse.from_item(item)


@router.post("/check", response_model=ConflictCheckResponse)
async def check_conflict(payload: ConflictCreateRequest) -> ConflictCheckResponse:
    item = service.detect_and_add(**payload.model_dump())
    if not item:
        return ConflictCheckResponse(conflict=False)
    return ConflictCheckResponse(conflict=True, item=ConflictResponse.from_item(item))


@router.post("/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: str, payload: ConflictResolveRequest
) -> ConflictResponse:
    item = service.resolve(conflict_id, payload.action)
    if not item:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return ConflictResponse.from_item(item)
