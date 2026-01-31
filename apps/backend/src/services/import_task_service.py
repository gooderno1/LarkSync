from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.services.feishu_client import FeishuClient


class ImportTaskError(RuntimeError):
    pass


@dataclass
class ImportTaskCreateResult:
    ticket: str


class ImportTaskService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def create_import_task(
        self,
        *,
        file_extension: str,
        file_token: str,
        mount_key: str,
        file_name: str | None = None,
        doc_type: str = "docx",
        mount_type: int = 1,
    ) -> ImportTaskCreateResult:
        extension = file_extension.strip().lstrip(".")
        if not extension:
            raise ImportTaskError("文件扩展名不能为空")
        if not file_token:
            raise ImportTaskError("file_token 不能为空")
        if not mount_key:
            raise ImportTaskError("mount_key 不能为空")

        payload: dict[str, Any] = {
            "file_extension": extension,
            "file_token": file_token,
            "type": doc_type,
            "point": {
                "mount_type": mount_type,
                "mount_key": mount_key,
            },
        }
        if file_name:
            payload["file_name"] = file_name

        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/import_tasks",
            json=payload,
        )
        data = response.get("data")
        if not isinstance(data, dict) or not data.get("ticket"):
            raise ImportTaskError("创建导入任务响应缺少 ticket")
        return ImportTaskCreateResult(ticket=str(data["ticket"]))

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            raise ImportTaskError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise ImportTaskError("飞书 API 响应格式错误")
        return payload

    async def close(self) -> None:
        await self._client.close()


__all__ = ["ImportTaskCreateResult", "ImportTaskError", "ImportTaskService"]
