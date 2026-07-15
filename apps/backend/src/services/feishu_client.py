from __future__ import annotations

import asyncio
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator
from urllib.parse import urlparse
from pathlib import Path

import httpx

from src.core.config import AppConfig, CloudWritePolicy, ConfigManager
from src.services.auth_service import AuthService
from src.services.rate_limiter import AsyncTokenBucket, get_global_rate_limiter

RETRYABLE_API_CODES = {1061045, 99991400}
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS"}
READ_ONLY_POST_PATHS = {
    "/open-apis/drive/v1/metas/batch_query",
    "/open-apis/drive/v1/export_tasks",
    "/open-apis/docx/v1/documents/blocks/convert",
}
_cloud_root_token: ContextVar[str | None] = ContextVar(
    "larksync_cloud_root_token", default=None
)


class CloudAccessDenied(RuntimeError):
    pass


@contextmanager
def cloud_root_scope(root_token: str) -> Iterator[None]:
    marker = activate_cloud_root_scope(root_token)
    try:
        yield
    finally:
        reset_cloud_root_scope(marker)


def activate_cloud_root_scope(root_token: str) -> Token[str | None]:
    return _cloud_root_token.set(root_token.strip())


def reset_cloud_root_scope(marker: Token[str | None]) -> None:
    _cloud_root_token.reset(marker)


class FeishuClient:
    def __init__(
        self,
        auth_service: AuthService | None = None,
        max_retries: int = 5,
        backoff_base: float = 0.5,
        backoff_factor: float = 2.0,
        config: AppConfig | None = None,
        rate_limiter: AsyncTokenBucket | None = None,
    ) -> None:
        self._auth_service = auth_service or AuthService()
        self._client = httpx.AsyncClient(timeout=30.0)
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_factor = backoff_factor
        self._config = config or ConfigManager.get().config
        self._rate_limiter = rate_limiter

    async def request(self, method: str, url: str, **kwargs):
        self._enforce_cloud_policy(method, url)
        limiter = self._rate_limiter or get_global_rate_limiter(
            self._config.feishu_rate_per_second,
            self._config.feishu_rate_burst,
        )
        await limiter.acquire()
        token = await self._auth_service.get_valid_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        response = await self._client.request(method, url, headers=headers, **kwargs)
        self._write_audit_record(method, url, response)
        return response

    def _write_audit_record(
        self, method: str, url: str, response: httpx.Response
    ) -> None:
        raw_path = (self._config.cloud_audit_log or "").strip()
        if not raw_path:
            return
        feishu_code = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                feishu_code = payload.get("code")
        except Exception:
            pass
        audit_path = Path(raw_path).expanduser().resolve()
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "profile": self._config.runtime_profile.value,
            "method": method.strip().upper(),
            "endpoint": urlparse(url).path,
            "http_status": response.status_code,
            "feishu_code": feishu_code,
        }
        with audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _enforce_cloud_policy(self, method: str, url: str) -> None:
        normalized_method = method.strip().upper()
        profile = self._config.runtime_profile.value
        if not self._config.cloud_access_allowed:
            raise CloudAccessDenied(f"运行配置 {profile} 禁止访问飞书云端")
        request_path = urlparse(url).path.rstrip("/")
        if normalized_method in SAFE_HTTP_METHODS or (
            normalized_method == "POST" and request_path in READ_ONLY_POST_PATHS
        ):
            return
        policy = self._config.effective_cloud_write_policy
        if policy is CloudWritePolicy.deny:
            raise CloudAccessDenied(f"运行配置 {profile} 为云端只读，禁止写请求")
        if policy is CloudWritePolicy.allowlisted:
            root_token = _cloud_root_token.get()
            if not root_token or root_token not in self._config.allowed_cloud_roots:
                raise CloudAccessDenied("云端写请求缺少有效的 allowlist 根目录作用域")

    async def request_with_retry(self, method: str, url: str, **kwargs):
        max_retries = max(1, kwargs.pop("max_retries", self._max_retries))
        for attempt in range(max_retries):
            response = await self.request(method, url, **kwargs)
            should_retry = response.status_code in RETRYABLE_STATUS_CODES
            if response.status_code == 429:
                should_retry = True
            if should_retry:
                if attempt < max_retries - 1:
                    await self._sleep_backoff(attempt, response)
                    continue
                return response
            try:
                payload = response.json()
            except Exception:
                return response
            if isinstance(payload, dict):
                code = payload.get("code")
                message = str(payload.get("msg", "")).lower()
                if code in RETRYABLE_API_CODES or "frequency limit" in message:
                    if attempt < max_retries - 1:
                        await self._sleep_backoff(attempt, response)
                        continue
                    return response
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
