from __future__ import annotations

from pathlib import Path

from src.services.feishu_client import FeishuClient
from src.services.file_writer import FileWriter
from src.services.path_sanitizer import sanitize_filename


class FileDownloader:
    def __init__(
        self,
        client: FeishuClient | None = None,
        writer: FileWriter | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._writer = writer or FileWriter()
        self._base_url = base_url.rstrip("/")

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
