import httpx
import pytest

from src.services.sheet_service import SheetService


class FakeClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, dict]] = []

    async def request_with_retry(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        if not self._responses:
            raise RuntimeError("no response prepared")
        return self._responses.pop(0)

    async def close(self) -> None:
        return None


def _build_response(payload: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", "https://open.feishu.cn"),
    )


@pytest.mark.asyncio
async def test_list_sheet_ids_returns_sorted_result() -> None:
    response = _build_response(
        {
            "code": 0,
            "data": {
                "sheets": [
                    {"sheet_id": "sheet-c", "index": 2},
                    {"sheet_id": "sheet-a", "index": 0},
                    {"sheet_id": "sheet-b", "index": 1},
                ]
            },
        }
    )
    client = FakeClient([response])
    service = SheetService(client=client)

    result = await service.list_sheet_ids("spreadsheet-token")

    assert result == ["sheet-a", "sheet-b", "sheet-c"]
    method, url, _ = client.requests[0]
    assert method == "GET"
    assert url.endswith("/open-apis/sheets/v3/spreadsheets/spreadsheet-token/sheets/query")


@pytest.mark.asyncio
async def test_get_sheet_meta_parses_grid_properties() -> None:
    response = _build_response(
        {
            "code": 0,
            "data": {
                "sheet": {
                    "sheet_id": "sheet-1",
                    "title": "阶段清单",
                    "grid_properties": {"row_count": 8, "column_count": 5},
                }
            },
        }
    )
    client = FakeClient([response])
    service = SheetService(client=client)

    meta = await service.get_sheet_meta("spreadsheet-token", "sheet-1")

    assert meta.sheet_id == "sheet-1"
    assert meta.title == "阶段清单"
    assert meta.row_count == 8
    assert meta.column_count == 5


@pytest.mark.asyncio
async def test_get_values_builds_a1_range_and_returns_rows() -> None:
    response = _build_response(
        {
            "code": 0,
            "data": {
                "valueRange": {
                    "range": "sheet-1!A1:AB3",
                    "values": [
                        ["名称", "状态"],
                        ["需求文档", "已完成"],
                    ],
                }
            },
        }
    )
    client = FakeClient([response])
    service = SheetService(client=client)

    rows = await service.get_values(
        "spreadsheet-token",
        "sheet-1",
        row_count=3,
        column_count=28,
    )

    assert rows == [["名称", "状态"], ["需求文档", "已完成"]]
    method, url, _ = client.requests[0]
    assert method == "GET"
    assert "/values/sheet-1%21A1%3AAB3" in url
