import httpx
import pytest

from src.services.import_task_service import ImportTaskError, ImportTaskService


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
async def test_create_import_task_payload() -> None:
    responses = [{"code": 0, "data": {"ticket": "ticket-123"}}]
    client = FakeClient(responses)
    service = ImportTaskService(client=client)

    result = await service.create_import_task(
        file_extension="md",
        file_token="file-1",
        mount_key="fld-1",
        file_name="测试文档",
        doc_type="docx",
    )

    assert result.ticket == "ticket-123"
    method, url, kwargs = client.requests[0]
    assert method == "POST"
    assert url.endswith("/open-apis/drive/v1/import_tasks")
    payload = kwargs["json"]
    assert payload["file_extension"] == "md"
    assert payload["file_token"] == "file-1"
    assert payload["type"] == "docx"
    assert payload["file_name"] == "测试文档"
    assert payload["point"]["mount_type"] == 1
    assert payload["point"]["mount_key"] == "fld-1"


@pytest.mark.asyncio
async def test_create_import_task_requires_ticket() -> None:
    responses = [{"code": 0, "data": {}}]
    client = FakeClient(responses)
    service = ImportTaskService(client=client)

    with pytest.raises(ImportTaskError):
        await service.create_import_task(
            file_extension="md",
            file_token="file-1",
            mount_key="fld-1",
        )


@pytest.mark.asyncio
async def test_create_import_task_requires_extension() -> None:
    client = FakeClient([])
    service = ImportTaskService(client=client)

    with pytest.raises(ImportTaskError):
        await service.create_import_task(
            file_extension="",
            file_token="file-1",
            mount_key="fld-1",
        )
    assert client.requests == []
