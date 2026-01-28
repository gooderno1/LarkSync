from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from src.core.config import AppConfig, ConfigManager
from src.core.security import TokenData, TokenStore, get_token_store


class AuthError(RuntimeError):
    pass


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_in: int | None


class AuthService:
    def __init__(
        self,
        config: AppConfig | None = None,
        token_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or ConfigManager.get().config
        self._token_store = token_store or get_token_store()
        self._http_client = http_client

    def build_authorize_url(self, state: str) -> str:
        if not self._config.auth_authorize_url:
            raise AuthError("auth_authorize_url 未配置")
        if not self._config.auth_client_id:
            raise AuthError("auth_client_id 未配置")
        if not self._config.auth_redirect_uri:
            raise AuthError("auth_redirect_uri 未配置")

        params = {
            "client_id": self._config.auth_client_id,
            "redirect_uri": self._config.auth_redirect_uri,
            "response_type": "code",
            "state": state,
        }
        if self._config.auth_scopes:
            params["scope"] = " ".join(self._config.auth_scopes)

        return f"{self._config.auth_authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> TokenData:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.auth_redirect_uri,
            "client_id": self._config.auth_client_id,
            "client_secret": self._config.auth_client_secret,
        }
        return await self._request_token(payload)

    async def refresh(self) -> TokenData:
        current = self._token_store.get()
        if not current:
            raise AuthError("缺少 refresh_token，请重新登录")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": current.refresh_token,
            "client_id": self._config.auth_client_id,
            "client_secret": self._config.auth_client_secret,
        }
        return await self._request_token(payload)

    def get_cached_token(self) -> TokenData | None:
        return self._token_store.get()

    async def get_valid_access_token(self) -> str:
        token = self._token_store.get()
        if token is None:
            raise AuthError("未登录，请先完成 OAuth 登录")
        if token.is_expired():
            token = await self.refresh()
        return token.access_token

    async def _request_token(self, payload: dict[str, str]) -> TokenData:
        if not self._config.auth_token_url:
            raise AuthError("auth_token_url 未配置")

        async with self._get_client() as client:
            response = await client.post(self._config.auth_token_url, data=payload)
            response.raise_for_status()
            data = response.json()

        token = self._parse_token_response(data)
        expires_at = None
        if token.expires_in is not None:
            expires_at = time.time() + token.expires_in

        stored = TokenData(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=expires_at,
        )
        self._token_store.set(stored)
        return stored

    def _parse_token_response(self, data: dict[str, object]) -> TokenResponse:
        if isinstance(data, dict):
            code = data.get("code")
            if isinstance(code, int) and code != 0:
                message = data.get("msg") or data.get("message") or "Token 接口返回错误"
                raise AuthError(f"{message} (code={code})")
            wrapped = data.get("data")
            if isinstance(wrapped, dict):
                data = wrapped

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")

        if not isinstance(access_token, str) or not access_token:
            raise AuthError("Token 响应缺少 access_token，请提供 API 响应样例")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise AuthError("Token 响应缺少 refresh_token，请提供 API 响应样例")

        expires_value: int | None = None
        if isinstance(expires_in, (int, float)):
            expires_value = int(expires_in)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_value,
        )

    def _get_client(self) -> httpx.AsyncClient:
        return self._http_client or httpx.AsyncClient(timeout=15.0)
