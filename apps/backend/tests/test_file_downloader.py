from pathlib import Path
from contextlib import asynccontextmanager
import hashlib

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


class StreamingClient:
    def __init__(self, body: bytes, status=200):
        self.response = httpx.Response(status, content=body)
        self.closed = False

    @asynccontextmanager
    async def stream(self, method, url):
        try:
            yield self.response
        finally:
            await self.response.aclose()
            self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"same", b"diff", b"short", b"much longer content"])
async def test_matches_file_requires_exact_size_and_hash(body):
    client = StreamingClient(body)
    downloader = FileDownloader(client=client)
    assert await downloader.matches_file(
        "word-token", expected_hash=hashlib.sha256(b"same").hexdigest(), expected_size=4,
    ) is (body == b"same")
    assert client.closed


@pytest.mark.asyncio
async def test_matches_file_does_not_treat_error_response_as_content():
    client = StreamingClient(b"denied", status=403)
    downloader = FileDownloader(client=client)
    with pytest.raises(RuntimeError, match="403"):
        await downloader.matches_file("word-token", expected_hash="hash", expected_size=6)
    assert client.closed


@pytest.mark.asyncio
async def test_matches_file_stops_reading_oversized_remote_content():
    class LargeStream(httpx.AsyncByteStream):
        def __init__(self):
            self.chunks_read = 0
            self.closed = False

        async def __aiter__(self):
            for _ in range(100):
                self.chunks_read += 1
                yield b"x" * (64 * 1024)

        async def aclose(self):
            self.closed = True

    stream = LargeStream()
    client = StreamingClient(b"")
    client.response = httpx.Response(200, stream=stream)
    downloader = FileDownloader(client=client)
    assert not await downloader.matches_file("token", expected_hash="hash", expected_size=18_770)
    assert stream.chunks_read == 1
    assert stream.closed
