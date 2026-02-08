from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.services.feishu_client import FeishuClient


class ExportTaskError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExportTaskCreateResult:
    ticket: str


@dataclass(frozen=True)
class ExportTaskResult:
    file_extension: str | None
    type: str | None
    file_name: str | None
    file_token: str | None
    file_size: int | None
    job_status: int | None
    job_error_msg: str | None


class ExportTaskService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def create_export_task(
        self,
        *,
        file_extension: str,
        file_token: str,
        file_type: str,
        sub_id: str | None = None,
    ) -> ExportTaskCreateResult:
        extension = file_extension.strip().lstrip(".")
        if not extension:
            raise ExportTaskError("文件扩展名不能为空")
        if not file_token:
            raise ExportTaskError("file_token 不能为空")
        if not file_type:
            raise ExportTaskError("type 不能为空")

        payload: dict[str, Any] = {
            "file_extension": extension,
            "token": file_token,
            "type": file_type,
        }
        if sub_id:
            payload["sub_id"] = sub_id

        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/export_tasks",
            json=payload,
        )
        data = response.get("data")
        if not isinstance(data, dict) or not data.get("ticket"):
            raise ExportTaskError("创建导出任务响应缺少 ticket")
        return ExportTaskCreateResult(ticket=str(data["ticket"]))

    async def get_export_task_result(self, ticket: str) -> ExportTaskResult:
        if not ticket:
            raise ExportTaskError("ticket 不能为空")
        response = await self._request_json(
            "GET",
            f"{self._base_url}/open-apis/drive/v1/export_tasks/{ticket}",
        )
        data = response.get("data") or {}
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, dict):
            raise ExportTaskError("导出任务响应缺少 result")
        return ExportTaskResult(
            file_extension=_as_str(result.get("file_extension")),
            type=_as_str(result.get("type")),
            file_name=_as_str(result.get("file_name")),
            file_token=_as_str(result.get("file_token")),
            file_size=_as_int(result.get("file_size")),
            job_status=_as_int(result.get("job_status")),
            job_error_msg=_as_str(result.get("job_error_msg")),
        )

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            raise ExportTaskError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise ExportTaskError("飞书 API 响应格式错误")
        return payload

    async def close(self) -> None:
        await self._client.close()


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "ExportTaskCreateResult",
    "ExportTaskError",
    "ExportTaskResult",
    "ExportTaskService",
]
