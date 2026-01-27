from __future__ import annotations

from pathlib import Path

from src.services.feishu_client import FeishuClient
from src.services.file_writer import FileWriter


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
        response = await self._client.request("GET", url)
        if response.status_code >= 400:
            raise RuntimeError(f"文件下载失败: HTTP {response.status_code}")

        target_path = target_dir / file_name
        self._writer.write_bytes(target_path, response.content, mtime)
        return target_path

    async def close(self) -> None:
        await self._client.close()


__all__ = ["FileDownloader"]
