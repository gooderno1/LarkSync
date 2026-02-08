from pathlib import Path

import httpx
import pytest

from src.services.file_downloader import FileDownloader


class FakeClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.requests: list[tuple[str, str, dict]] = []

    async def request(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        return self._response

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_download_file_writes_bytes_and_mtime(tmp_path: Path) -> None:
    response = httpx.Response(200, content=b"binary")
    client = FakeClient(response)
    downloader = FileDownloader(client=client)

    target = await downloader.download(
        file_token="file-token",
        file_name="demo.pdf",
        target_dir=tmp_path,
        mtime=1700000000.0,
    )

    assert target.read_bytes() == b"binary"
    assert abs(target.stat().st_mtime - 1700000000.0) < 1.0


@pytest.mark.asyncio
async def test_download_exported_file_writes_bytes_and_mtime(tmp_path: Path) -> None:
    response = httpx.Response(200, content=b"exported")
    client = FakeClient(response)
    downloader = FileDownloader(client=client)

    target = await downloader.download_exported_file(
        file_token="export-token",
        file_name="report.xlsx",
        target_dir=tmp_path,
        mtime=1700001234.0,
    )

    assert target.read_bytes() == b"exported"
    assert abs(target.stat().st_mtime - 1700001234.0) < 1.0
