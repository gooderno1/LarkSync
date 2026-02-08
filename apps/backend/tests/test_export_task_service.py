import httpx
import pytest

from src.services.export_task_service import (
    ExportTaskError,
    ExportTaskService,
)


class FakeClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.requests: list[tuple[str, str, dict]] = []

    async def request_with_retry(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        return self._response

    async def close(self) -> None:
        return None


def _build_response(payload: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", "https://open.feishu.cn"),
    )


@pytest.mark.asyncio
async def test_create_export_task_builds_payload() -> None:
    response = _build_response({"code": 0, "data": {"ticket": "t-1"}})
    client = FakeClient(response)
    service = ExportTaskService(client=client)

    result = await service.create_export_task(
        file_extension=".xlsx",
        file_token="file-token",
        file_type="sheet",
    )

    assert result.ticket == "t-1"
    method, url, kwargs = client.requests[0]
    assert method == "POST"
    assert url.endswith("/open-apis/drive/v1/export_tasks")
    assert kwargs["json"]["file_extension"] == "xlsx"
    assert kwargs["json"]["token"] == "file-token"
    assert kwargs["json"]["type"] == "sheet"


@pytest.mark.asyncio
async def test_create_export_task_requires_params() -> None:
    response = _build_response({"code": 0, "data": {"ticket": "t-1"}})
    service = ExportTaskService(client=FakeClient(response))

    with pytest.raises(ExportTaskError):
        await service.create_export_task(
            file_extension="",
            file_token="file-token",
            file_type="sheet",
        )

    with pytest.raises(ExportTaskError):
        await service.create_export_task(
            file_extension="xlsx",
            file_token="",
            file_type="sheet",
        )

    with pytest.raises(ExportTaskError):
        await service.create_export_task(
            file_extension="xlsx",
            file_token="file-token",
            file_type="",
        )


@pytest.mark.asyncio
async def test_get_export_task_result_parses_response() -> None:
    response = _build_response(
        {
            "code": 0,
            "data": {
                "result": {
                    "file_extension": "xlsx",
                    "type": "sheet",
                    "file_name": "demo.xlsx",
                    "file_token": "file-token",
                    "file_size": 123,
                    "job_status": 0,
                    "job_error_msg": "",
                }
            },
        }
    )
    client = FakeClient(response)
    service = ExportTaskService(client=client)

    result = await service.get_export_task_result("ticket-1")

    assert result.file_extension == "xlsx"
    assert result.type == "sheet"
    assert result.file_name == "demo.xlsx"
    assert result.file_token == "file-token"
    assert result.file_size == 123
    assert result.job_status == 0
