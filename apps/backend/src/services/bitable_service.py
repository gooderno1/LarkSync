from __future__ import annotations

from typing import Any

from src.services.feishu_client import FeishuClient


class BitableService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def list_table_ids(self, app_token: str) -> list[str]:
        if not app_token:
            return []
        url = f"{self._base_url}/open-apis/bitable/v1/apps/{app_token}/tables"
        page_token: str | None = None
        table_ids: list[str] = []
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            response = await self._client.request("GET", url, params=params)
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"获取多维表格失败: {payload.get('msg')}")
            data = payload.get("data") or {}
            items = data.get("items") or data.get("tables") or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                table_id = item.get("table_id") or item.get("id")
                if table_id:
                    table_ids.append(str(table_id))
            has_more = bool(data.get("has_more"))
            if not has_more:
                break
            page_token = data.get("page_token") or data.get("next_page_token")
            if not page_token:
                break
        return table_ids

    async def close(self) -> None:
        await self._client.close()


__all__ = ["BitableService"]
