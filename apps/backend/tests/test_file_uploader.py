import httpx
import pytest

from src.db.models import SyncMapping
from src.db.session import get_session_maker, init_db
from src.services.file_uploader import FileUploader


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, dict]] = []

    async def request_with_retry(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        payload = self._responses.pop(0)
        request = httpx.Request(method, url)
        return httpx.Response(200, json=payload, request=request)

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_upload_all_small_file(tmp_path) -> None:
    responses = [{"code": 0, "data": {"file_token": "token-123"}}]
    client = FakeClient(responses)
    uploader = FileUploader(client=client, simple_upload_limit=10)

    file_path = tmp_path / "small.txt"
    file_path.write_text("hello", encoding="utf-8")

    result = await uploader.upload_file(file_path, parent_node="fld123", record_db=False)
    assert result.file_token == "token-123"

    method, url, kwargs = client.requests[0]
    assert method == "POST"
    assert url.endswith("/open-apis/drive/v1/files/upload_all")
    assert kwargs["data"]["file_name"] == "small.txt"
    assert kwargs["data"]["parent_type"] == "explorer"
    assert kwargs["data"]["parent_node"] == "fld123"
    assert "files" in kwargs


@pytest.mark.asyncio
async def test_upload_multipart_large_file(tmp_path) -> None:
    responses = [
        {"code": 0, "data": {"upload_id": "upload-1", "block_size": 2, "block_num": 2}},
        {"code": 0, "data": {}},
        {"code": 0, "data": {}},
        {"code": 0, "data": {"file_token": "token-456"}},
    ]
    client = FakeClient(responses)
    uploader = FileUploader(client=client, simple_upload_limit=1)

    file_path = tmp_path / "large.bin"
    file_path.write_bytes(b"abc")

    result = await uploader.upload_file(file_path, parent_node="fld456", record_db=False)
    assert result.file_token == "token-456"

    assert client.requests[0][1].endswith("/open-apis/drive/v1/files/upload_prepare")
    assert client.requests[1][1].endswith("/open-apis/drive/v1/files/upload_part")
    assert client.requests[2][1].endswith("/open-apis/drive/v1/files/upload_part")
    assert client.requests[3][1].endswith("/open-apis/drive/v1/files/upload_finish")


@pytest.mark.asyncio
async def test_upload_records_sync_mapping(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)

    responses = [{"code": 0, "data": {"file_token": "token-999"}}]
    client = FakeClient(responses)
    uploader = FileUploader(client=client, simple_upload_limit=10, session_maker=session_maker)

    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"data")

    result = await uploader.upload_file(file_path, parent_node="fld999", record_db=True)

    async with session_maker() as session:
        mapping = await session.get(SyncMapping, result.file_hash)
        assert mapping is not None
        assert mapping.feishu_token == "token-999"
        assert mapping.local_path == str(file_path)
