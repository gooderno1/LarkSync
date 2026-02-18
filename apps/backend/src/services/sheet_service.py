from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from src.services.feishu_client import FeishuClient


@dataclass(frozen=True)
class SheetMeta:
    sheet_id: str
    title: str
    row_count: int
    column_count: int


class SheetService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def list_sheet_ids(self, spreadsheet_token: str) -> list[str]:
        if not spreadsheet_token:
            return []
        url = (
            f"{self._base_url}/open-apis/sheets/v3/spreadsheets/"
            f"{spreadsheet_token}/sheets/query"
        )
        response = await self._client.request_with_retry("GET", url)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"获取电子表格失败: {payload.get('msg')}")
        data = payload.get("data") or {}
        sheets = data.get("sheets") or []
        collected: list[tuple[int, str]] = []
        for sheet in sheets:
            if not isinstance(sheet, dict):
                continue
            sheet_id = sheet.get("sheet_id") or sheet.get("id")
            if not sheet_id:
                continue
            index = sheet.get("index")
            try:
                order = int(index)
            except (TypeError, ValueError):
                order = 0
            collected.append((order, str(sheet_id)))
        collected.sort(key=lambda item: item[0])
        return [sheet_id for _, sheet_id in collected]

    async def get_sheet_meta(
        self,
        spreadsheet_token: str,
        sheet_id: str,
    ) -> SheetMeta:
        if not spreadsheet_token:
            raise RuntimeError("spreadsheet_token 不能为空")
        if not sheet_id:
            raise RuntimeError("sheet_id 不能为空")
        url = (
            f"{self._base_url}/open-apis/sheets/v3/spreadsheets/"
            f"{spreadsheet_token}/sheets/{sheet_id}"
        )
        response = await self._client.request_with_retry("GET", url)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"获取子表元信息失败: {payload.get('msg')}")
        data = payload.get("data") or {}
        sheet = data.get("sheet") or {}
        grid = sheet.get("grid_properties") or {}
        row_count = _as_positive_int(grid.get("row_count"), default=1)
        column_count = _as_positive_int(grid.get("column_count"), default=1)
        title = str(sheet.get("title") or sheet_id)
        return SheetMeta(
            sheet_id=str(sheet.get("sheet_id") or sheet_id),
            title=title,
            row_count=row_count,
            column_count=column_count,
        )

    async def get_values(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        *,
        row_count: int,
        column_count: int,
    ) -> list[list[object]]:
        if not spreadsheet_token:
            raise RuntimeError("spreadsheet_token 不能为空")
        if not sheet_id:
            raise RuntimeError("sheet_id 不能为空")
        rows = _as_positive_int(row_count, default=1)
        cols = _as_positive_int(column_count, default=1)
        end_col = _column_to_name(cols)
        range_ref = f"{sheet_id}!A1:{end_col}{rows}"
        encoded_range = quote(range_ref, safe="")
        url = (
            f"{self._base_url}/open-apis/sheets/v2/spreadsheets/"
            f"{spreadsheet_token}/values/{encoded_range}"
        )
        response = await self._client.request_with_retry("GET", url)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"获取子表单元格失败: {payload.get('msg')}")
        data = payload.get("data") or {}
        value_range = data.get("valueRange") or {}
        values = value_range.get("values") or []
        result: list[list[object]] = []
        if not isinstance(values, list):
            return result
        for row in values:
            if isinstance(row, list):
                result.append(row)
            elif row is None:
                result.append([])
            else:
                result.append([row])
        return result

    async def close(self) -> None:
        await self._client.close()


def _as_positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _column_to_name(index: int) -> str:
    current = max(1, int(index))
    letters: list[str] = []
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


__all__ = ["SheetMeta", "SheetService"]
