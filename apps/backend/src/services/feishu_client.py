from __future__ import annotations

import httpx

from src.services.auth_service import AuthService


class FeishuClient:
    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._auth_service = auth_service or AuthService()
        self._client = httpx.AsyncClient(timeout=30.0)

    async def request(self, method: str, url: str, **kwargs):
        token = await self._auth_service.get_valid_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        return await self._client.request(method, url, headers=headers, **kwargs)

    async def close(self) -> None:
        await self._client.aclose()
