from __future__ import annotations

from typing import Any

from src.services.feishu_client import FeishuClient


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
        response = await self._client.request("GET", url)
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

    async def close(self) -> None:
        await self._client.close()


__all__ = ["SheetService"]
