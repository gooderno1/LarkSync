from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from loguru import logger

from src.core.config import AppConfig, ConfigManager
from src.core.security import TokenData, TokenStore, get_token_store


class AuthError(RuntimeError):
    pass


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str  # 可为空字符串（飞书 v2 可能不返回）
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

    @staticmethod
    def _require_config(value: str, label: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise AuthError(f"{label} 未配置")
        return cleaned

    def build_authorize_url(self, state: str) -> str:
        authorize_url = self._require_config(
            self._config.auth_authorize_url, "auth_authorize_url"
        )
        app_id = self._require_config(self._config.auth_client_id, "auth_client_id")
        redirect_uri = self._require_config(
            self._config.auth_redirect_uri, "auth_redirect_uri"
        )

        # 飞书 v1 OAuth：使用 app_id 参数
        params: dict[str, str] = {
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }

        url = f"{authorize_url}?{urlencode(params)}"
        logger.info("授权 URL（脱敏）: {}...&state=***", url.split("&state=")[0])
        return url

    async def exchange_code(self, code: str) -> TokenData:
        app_id = self._require_config(self._config.auth_client_id, "auth_client_id")
        app_secret = self._require_config(
            self._config.auth_client_secret, "auth_client_secret"
        )
        # 飞书 v1 OAuth：使用 app_id / app_secret
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": app_id,
            "app_secret": app_secret,
        }
        return await self._request_token(payload)

    async def refresh(self) -> TokenData:
        current = self._token_store.get()
        if not current:
            raise AuthError("缺少登录凭证，请重新登录")
        if not current.refresh_token:
            raise AuthError("refresh_token 不可用，请重新登录")
        app_id = self._require_config(self._config.auth_client_id, "auth_client_id")
        app_secret = self._require_config(
            self._config.auth_client_secret, "auth_client_secret"
        )
        # 飞书 v1 OAuth：使用 app_id / app_secret
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": current.refresh_token,
            "app_id": app_id,
            "app_secret": app_secret,
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
        token_url = self._require_config(self._config.auth_token_url, "auth_token_url")

        async with self._get_client() as client:
            try:
                response = await client.post(token_url, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                message = self._format_http_error(exc.response)
                raise AuthError(message) from exc
            except httpx.RequestError as exc:
                raise AuthError(f"Token 请求失败：{exc}") from exc
            try:
                data = response.json()
            except ValueError as exc:
                snippet = response.text[:200]
                raise AuthError(f"Token 响应不是 JSON：{snippet}") from exc

        # 记录响应结构（脱敏）用于调试
        self._log_token_response(data)

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

    @staticmethod
    def _log_token_response(data: dict[str, object]) -> None:
        """记录 token 响应的键和值类型（脱敏），方便排查飞书端点变化。"""
        try:
            sanitized: dict[str, str] = {}
            target = data
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                sanitized["_envelope"] = "code={}, keys={}".format(
                    data.get("code"), list(data.keys())
                )
                target = data["data"]  # type: ignore[assignment]
            for k, v in (target if isinstance(target, dict) else {}).items():
                if isinstance(v, str) and len(v) > 8:
                    sanitized[k] = f"{type(v).__name__}({len(v)}): {v[:4]}...{v[-4:]}"
                else:
                    sanitized[k] = repr(v)
            logger.debug("Token 响应结构（脱敏）: {}", sanitized)
        except Exception:  # noqa: BLE001
            logger.debug("Token 响应记录失败，原始 keys: {}", list(data.keys()) if isinstance(data, dict) else type(data))

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

        # refresh_token 在飞书 v2 端点中可能不存在，设为可选
        refresh_token_value = ""
        if isinstance(refresh_token, str) and refresh_token:
            refresh_token_value = refresh_token
        else:
            logger.warning(
                "Token 响应未包含 refresh_token（类型={}），令牌过期后需重新授权",
                type(refresh_token).__name__,
            )

        expires_value: int | None = None
        if isinstance(expires_in, (int, float)):
            expires_value = int(expires_in)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_value,
            expires_in=expires_value,
        )

    def _format_http_error(self, response: httpx.Response) -> str:
        message = f"Token 请求失败（HTTP {response.status_code}）"
        try:
            payload = response.json()
        except ValueError:
            body = response.text.strip()
            return f"{message}：{body}" if body else message

        if isinstance(payload, dict):
            code = payload.get("code")
            msg = payload.get("msg") or payload.get("message")
            error = payload.get("error") or payload.get("error_description")
            detail_parts: list[str] = []
            if msg:
                detail_parts.append(str(msg))
            if error:
                detail_parts.append(str(error))
            if code is not None:
                detail_parts.append(f"code={code}")
            if detail_parts:
                return f"{message}：{' '.join(detail_parts)}"

        return f"{message}：{payload}"

    def _get_client(self) -> httpx.AsyncClient:
        return self._http_client or httpx.AsyncClient(timeout=15.0)
