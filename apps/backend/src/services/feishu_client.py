from __future__ import annotations

import asyncio
import httpx

from src.services.auth_service import AuthService


class FeishuClient:
    def __init__(
        self,
        auth_service: AuthService | None = None,
        max_retries: int = 5,
        backoff_base: float = 0.5,
        backoff_factor: float = 2.0,
    ) -> None:
        self._auth_service = auth_service or AuthService()
        self._client = httpx.AsyncClient(timeout=30.0)
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_factor = backoff_factor

    async def request(self, method: str, url: str, **kwargs):
        token = await self._auth_service.get_valid_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        return await self._client.request(method, url, headers=headers, **kwargs)

    async def request_with_retry(self, method: str, url: str, **kwargs):
        max_retries = kwargs.pop("max_retries", self._max_retries)
        for attempt in range(max_retries):
            response = await self.request(method, url, **kwargs)
            if response.status_code == 429:
                await self._sleep_backoff(attempt, response)
                continue
            try:
                payload = response.json()
            except Exception:
                return response
            if isinstance(payload, dict) and payload.get("code") == 1061045:
                await self._sleep_backoff(attempt, response)
                continue
            return response
        return response

    async def close(self) -> None:
        await self._client.aclose()

    async def _sleep_backoff(self, attempt: int, response: httpx.Response) -> None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                delay = float(retry_after)
                if delay > 0:
                    await asyncio.sleep(delay)
                    return
            except ValueError:
                pass
        delay = self._backoff_base * (self._backoff_factor**attempt)
        await asyncio.sleep(delay)
