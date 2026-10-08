from __future__ import annotations

import hashlib
from pathlib import Path

from src.services.feishu_client import FeishuClient
from src.services.file_writer import FileWriter
from src.services.path_sanitizer import sanitize_filename
from src.services.account_runtime import current_open_base_url


class FileDownloader:
    def __init__(
        self,
        client: FeishuClient | None = None,
        writer: FileWriter | None = None,
        base_url: str | None = None,
    ) -> None:
        self._client = client or FeishuClient()
        self._writer = writer or FileWriter()
        self._base_url = (base_url or current_open_base_url()).rstrip("/")

    async def download(
        self,
        file_token: str,
        file_name: str,
        target_dir: Path,
        mtime: float,
    ) -> Path:
        url = f"{self._base_url}/open-apis/drive/v1/files/{file_token}/download"
        return await self._download_to_path(url, file_name, target_dir, mtime)

    async def download_exported_file(
        self,
        file_token: str,
        file_name: str,
        target_dir: Path,
        mtime: float,
    ) -> Path:
        url = (
            f"{self._base_url}/open-apis/drive/v1/export_tasks/file/{file_token}/download"
        )
        return await self._download_to_path(url, file_name, target_dir, mtime)

    async def matches_file(
        self, file_token: str, *, expected_hash: str, expected_size: int,
    ) -> bool:
        """Verify binary content without writing files or buffering the response."""
        url = f"{self._base_url}/open-apis/drive/v1/files/{file_token}/download"
        async with self._client.stream("GET", url) as response:
            if response.status_code != 200:
                raise RuntimeError(f"文件核验下载失败: HTTP {response.status_code}")
            hasher = hashlib.sha256()
            size = 0
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                size += len(chunk)
                if size > expected_size:
                    return False
                hasher.update(chunk)
            return size == expected_size and hasher.hexdigest() == expected_hash

    async def _download_to_path(
        self,
        url: str,
        file_name: str,
        target_dir: Path,
        mtime: float,
    ) -> Path:
        response = await self._client.request("GET", url)
        if response.status_code >= 400:
            raise RuntimeError(f"文件下载失败: HTTP {response.status_code}")

        safe_name = sanitize_filename(file_name)
        target_path = target_dir / safe_name
        self._writer.write_bytes(target_path, response.content, mtime)
        return target_path

    async def close(self) -> None:
        await self._client.close()


__all__ = ["FileDownloader"]
