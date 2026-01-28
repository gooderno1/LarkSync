from __future__ import annotations

import zlib
from pathlib import Path
from typing import Any

from src.services.feishu_client import FeishuClient


class MediaUploadError(RuntimeError):
    pass


class MediaUploader:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
        default_parent_type: str = "docx_image",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")
        self._default_parent_type = default_parent_type

    async def upload_image(
        self,
        file_path: str | Path,
        parent_node: str,
        parent_type: str | None = None,
    ) -> str:
        path = Path(file_path)
        if not path.exists():
            raise MediaUploadError(f"图片不存在: {path}")
        file_bytes = path.read_bytes()
        if not file_bytes:
            raise MediaUploadError("图片大小不能为空")

        data = {
            "file_name": path.name,
            "parent_type": parent_type or self._default_parent_type,
            "parent_node": parent_node,
            "size": str(len(file_bytes)),
            "checksum": self._adler32(file_bytes),
        }
        files = {"file": (path.name, file_bytes)}
        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/medias/upload_all",
            data=data,
            files=files,
        )
        payload = response.get("data")
        if not isinstance(payload, dict) or not payload.get("file_token"):
            raise MediaUploadError("上传素材响应缺少 file_token")
        return str(payload["file_token"])

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            raise MediaUploadError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise MediaUploadError("飞书 API 响应格式错误")
        return payload

    @staticmethod
    def _adler32(content: bytes) -> str:
        return str(zlib.adler32(content) & 0xFFFFFFFF)


__all__ = ["MediaUploader", "MediaUploadError"]
