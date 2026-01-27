from __future__ import annotations

import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.db.models import SyncMapping
from src.db.session import get_session_maker
from src.services.feishu_client import FeishuClient
from src.services.file_hash import calculate_file_hash


class FileUploadError(RuntimeError):
    pass


@dataclass
class UploadResult:
    file_token: str
    file_hash: str


class FileUploader:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
        simple_upload_limit: int = 20 * 1024 * 1024,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")
        self._simple_upload_limit = simple_upload_limit
        self._session_maker = session_maker

    async def upload_file(
        self,
        file_path: str | Path,
        parent_node: str,
        parent_type: str = "explorer",
        record_db: bool = True,
    ) -> UploadResult:
        path = Path(file_path)
        if not path.exists():
            raise FileUploadError(f"文件不存在: {path}")
        file_size = path.stat().st_size
        if file_size <= 0:
            raise FileUploadError("文件大小不能为空")

        if file_size <= self._simple_upload_limit:
            file_token = await self._upload_all(path, parent_node, parent_type)
        else:
            file_token = await self._upload_multipart(path, parent_node, parent_type)

        file_hash = calculate_file_hash(path)
        if record_db:
            await self._record_mapping(
                file_hash=file_hash,
                file_token=file_token,
                local_path=str(path),
                mtime=path.stat().st_mtime,
            )

        return UploadResult(file_token=file_token, file_hash=file_hash)

    async def _upload_all(
        self, path: Path, parent_node: str, parent_type: str
    ) -> str:
        file_bytes = path.read_bytes()
        data = {
            "file_name": path.name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": str(len(file_bytes)),
            "checksum": self._adler32(file_bytes),
        }
        files = {"file": (path.name, file_bytes)}
        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/files/upload_all",
            data=data,
            files=files,
        )
        data = response.get("data")
        if not isinstance(data, dict) or not data.get("file_token"):
            raise FileUploadError("上传文件响应缺少 file_token")
        return str(data["file_token"])

    async def _upload_multipart(
        self, path: Path, parent_node: str, parent_type: str
    ) -> str:
        prepare_payload = {
            "file_name": path.name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": path.stat().st_size,
        }
        prepare = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/files/upload_prepare",
            json=prepare_payload,
        )
        prepare_data = prepare.get("data")
        if not isinstance(prepare_data, dict):
            raise FileUploadError("预上传响应缺少 data")
        upload_id = prepare_data.get("upload_id")
        block_size = prepare_data.get("block_size")
        block_num = prepare_data.get("block_num")
        if not upload_id or not block_size or not block_num:
            raise FileUploadError("预上传响应缺少必要字段")

        with path.open("rb") as handle:
            seq = 0
            while True:
                chunk = handle.read(int(block_size))
                if not chunk:
                    break
                data = {
                    "upload_id": upload_id,
                    "seq": seq,
                    "size": len(chunk),
                    "checksum": self._adler32(chunk),
                }
                files = {"file": (path.name, chunk)}
                await self._request_json(
                    "POST",
                    f"{self._base_url}/open-apis/drive/v1/files/upload_part",
                    data=data,
                    files=files,
                )
                seq += 1

        finish_payload = {"upload_id": upload_id, "block_num": block_num}
        finish = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/drive/v1/files/upload_finish",
            json=finish_payload,
        )
        finish_data = finish.get("data")
        if not isinstance(finish_data, dict) or not finish_data.get("file_token"):
            raise FileUploadError("完成上传响应缺少 file_token")
        return str(finish_data["file_token"])

    async def _record_mapping(
        self, file_hash: str, file_token: str, local_path: str, mtime: float
    ) -> None:
        session_maker = self._session_maker or get_session_maker()
        async with session_maker() as session:
            mapping = await session.get(SyncMapping, file_hash)
            if mapping:
                mapping.feishu_token = file_token
                mapping.local_path = local_path
                mapping.last_sync_mtime = mtime
            else:
                session.add(
                    SyncMapping(
                        file_hash=file_hash,
                        feishu_token=file_token,
                        local_path=local_path,
                        last_sync_mtime=mtime,
                        version=0,
                    )
                )
            await session.commit()

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            raise FileUploadError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise FileUploadError("飞书 API 响应格式错误")
        return payload

    @staticmethod
    def _adler32(content: bytes) -> str:
        return str(zlib.adler32(content) & 0xFFFFFFFF)
