from __future__ import annotations

import asyncio
import hashlib
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import AsyncIterator, ClassVar, Protocol
from urllib.parse import urlencode

import httpx
from loguru import logger

from src.core.config import AppConfig, ConfigManager
from src.core.paths import _default_app_data_dir
from src.core.process_lock import InterProcessFileLock
from src.core.security import TokenData, TokenStore, get_token_store
from src.core.account_context import current_account_id
from src.services.account_runtime import account_runtime_registry
from src.services.device_flow_service import open_base_url


class AuthError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ProcessLock(Protocol):
    def acquire(self) -> None: ...

    def release(self) -> None: ...


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str  # 可为空字符串（飞书 v2 可能不返回）
    expires_in: int | None
    open_id: str | None


@dataclass
class UserProfile:
    open_id: str | None = None
    account_name: str | None = None


class AuthService:
    _refresh_locks: ClassVar[dict[int, asyncio.Lock]] = {}
    _refresh_locks_guard: ClassVar[Lock] = Lock()

    def __init__(
        self,
        config: AppConfig | None = None,
        token_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
        process_lock: ProcessLock | None = None,
    ) -> None:
        account_id = current_account_id()
        runtime = account_runtime_registry.get(account_id) if config is None else None
        self._config = config or (
            runtime.app_config() if runtime else ConfigManager.get().config
        )
        self._brand = (
            runtime.brand
            if runtime
            else ("lark" if "larksuite.com" in self._config.auth_token_url else "feishu")
        )
        self._token_store = token_store or get_token_store(account_id)
        self._http_client = http_client
        self._process_lock = process_lock or InterProcessFileLock(
            self._refresh_lock_path(
                f"{self._config.auth_client_id}-{account_id or 'legacy'}"
            )
        )

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

        if self._uses_v2_oauth():
            scopes = list(dict.fromkeys([*self._config.auth_scopes, "offline_access"]))
            params: dict[str, str] = {
                "client_id": app_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state,
            }
        else:
            # 飞书历史 v1 OAuth：使用 app_id 参数。
            params = {
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
        if self._uses_v2_oauth():
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": self._require_config(
                    self._config.auth_redirect_uri,
                    "auth_redirect_uri",
                ),
            }
        else:
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "app_id": app_id,
                "app_secret": app_secret,
            }
        async with self._get_refresh_lock():
            async with self._hold_process_lock():
                await asyncio.to_thread(self._token_store.reload)
                return await self._request_token(payload)

    async def refresh(self) -> TokenData:
        async with self._get_refresh_lock():
            async with self._hold_process_lock():
                current = await asyncio.to_thread(self._token_store.reload)
                return await self._refresh_with_recovery(current)

    def get_cached_token(self) -> TokenData | None:
        return self._token_store.get()

    async def logout(self) -> None:
        async with self._get_refresh_lock():
            async with self._hold_process_lock():
                await asyncio.to_thread(self._token_store.clear)

    async def get_valid_access_token(self) -> str:
        token = self._token_store.get()
        if token is None:
            raise AuthError("未登录，请先完成 OAuth 登录")
        if not token.is_expired():
            return token.access_token
        async with self._get_refresh_lock():
            async with self._hold_process_lock():
                latest = await asyncio.to_thread(self._token_store.reload)
                if latest is None:
                    raise AuthError("未登录，请先完成 OAuth 登录")
                if not latest.is_expired():
                    return latest.access_token
                refreshed = await self._refresh_with_recovery(latest)
                return refreshed.access_token

    async def ensure_cached_identity(self) -> TokenData | None:
        """确保缓存凭证里带有身份信息；缺失时通过用户信息接口补齐。"""
        token = self._token_store.get()
        if token is None:
            return None
        if token.open_id and token.account_name:
            return token
        access_token = await self.get_valid_access_token()
        latest = self._token_store.get() or token
        if latest.open_id and latest.account_name:
            return latest
        profile = await self._fetch_user_profile(access_token)
        async with self._get_refresh_lock():
            async with self._hold_process_lock():
                latest = await asyncio.to_thread(self._token_store.reload)
                if latest is None:
                    return None
                resolved_open_id = latest.open_id or profile.open_id
                resolved_account_name = latest.account_name or profile.account_name
                if (
                    resolved_open_id == latest.open_id
                    and resolved_account_name == latest.account_name
                ):
                    return latest
                updated = TokenData(
                    access_token=latest.access_token,
                    refresh_token=latest.refresh_token,
                    expires_at=latest.expires_at,
                    open_id=resolved_open_id,
                    account_name=resolved_account_name,
                    scope=latest.scope,
                    refresh_expires_at=latest.refresh_expires_at,
                )
                await asyncio.to_thread(self._token_store.set, updated)
                return updated

    async def _request_token(self, payload: dict[str, str]) -> TokenData:
        token_url = self._require_config(self._config.auth_token_url, "auth_token_url")
        previous = await asyncio.to_thread(self._token_store.get)
        request_started = time.perf_counter()

        async with self._get_client() as client:
            try:
                response = await client.post(token_url, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                message = self._format_http_error(exc.response)
                raise AuthError(
                    message,
                    code=self._extract_error_code(exc.response),
                ) from exc
            except httpx.RequestError as exc:
                raise AuthError(f"Token 请求失败：{exc}") from exc
            try:
                data = response.json()
            except ValueError as exc:
                snippet = response.text[:200]
                raise AuthError(f"Token 响应不是 JSON：{snippet}") from exc
        logger.info(
            "OAuth token 交换完成: elapsed_ms={:.1f}",
            (time.perf_counter() - request_started) * 1000,
        )

        # 记录响应结构（脱敏）用于调试
        self._log_token_response(data)

        token = self._parse_token_response(data)
        expires_at = None
        if token.expires_in is not None:
            expires_at = time.time() + token.expires_in

        resolved_open_id = token.open_id or (previous.open_id if previous else None)
        resolved_account_name = previous.account_name if previous else None
        resolved_refresh_token = token.refresh_token
        if (
            not resolved_refresh_token
            and previous is not None
            and previous.refresh_token
        ):
            resolved_refresh_token = previous.refresh_token
            logger.warning("Token 响应缺少 refresh_token，继续保留当前 refresh_token")
        stored = TokenData(
            access_token=token.access_token,
            refresh_token=resolved_refresh_token,
            expires_at=expires_at,
            open_id=resolved_open_id,
            account_name=resolved_account_name,
            scope=previous.scope if previous else None,
            refresh_expires_at=(previous.refresh_expires_at if previous else None),
        )
        persist_started = time.perf_counter()
        await asyncio.to_thread(self._token_store.set, stored)
        logger.info(
            "OAuth token 安全存储完成: elapsed_ms={:.1f}",
            (time.perf_counter() - persist_started) * 1000,
        )
        return stored

    async def _refresh_unlocked(self, current: TokenData | None) -> TokenData:
        if not current:
            raise AuthError("缺少登录凭证，请重新登录")
        if not current.refresh_token:
            raise AuthError("refresh_token 不可用，请重新登录")
        app_id = self._require_config(self._config.auth_client_id, "auth_client_id")
        app_secret = self._require_config(
            self._config.auth_client_secret, "auth_client_secret"
        )
        if self._uses_v2_oauth():
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": current.refresh_token,
                "client_id": app_id,
                "client_secret": app_secret,
            }
        else:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": current.refresh_token,
                "app_id": app_id,
                "app_secret": app_secret,
            }
        return await self._request_token(payload)

    def _uses_v2_oauth(self) -> bool:
        return "/authen/v2/oauth/token" in self._config.auth_token_url.strip().lower()

    async def _refresh_with_recovery(self, current: TokenData | None) -> TokenData:
        attempted = current
        try:
            return await self._refresh_unlocked(current)
        except AuthError as exc:
            if exc.code not in {"20026", "20064", "20073"}:
                raise
            latest = await asyncio.to_thread(self._token_store.reload)
            if self._refresh_token_changed(attempted, latest):
                logger.warning(
                    "检测到其他进程已轮换 OAuth token: old={} new={} code={}",
                    self._token_fingerprint(attempted),
                    self._token_fingerprint(latest),
                    exc.code,
                )
                if latest is not None and not latest.is_expired():
                    return latest
                try:
                    return await self._refresh_unlocked(latest)
                except AuthError as retry_exc:
                    raise self._reauthorization_error(retry_exc) from retry_exc
            raise self._reauthorization_error(exc) from exc

    @asynccontextmanager
    async def _hold_process_lock(self) -> AsyncIterator[None]:
        started = time.perf_counter()
        try:
            await asyncio.to_thread(self._process_lock.acquire)
        except TimeoutError as exc:
            raise AuthError("OAuth 凭证正在被其他进程更新，请稍后重试") from exc
        logger.debug(
            "OAuth 跨进程锁已获取: pid={} wait_ms={:.1f}",
            os.getpid(),
            (time.perf_counter() - started) * 1000,
        )
        try:
            yield
        finally:
            await asyncio.shield(asyncio.to_thread(self._process_lock.release))

    @staticmethod
    def _refresh_lock_path(app_id: str) -> Path:
        namespace = hashlib.sha256(
            (app_id.strip() or "unconfigured").encode("utf-8")
        ).hexdigest()[:16]
        return _default_app_data_dir() / "locks" / f"oauth-refresh-{namespace}.lock"

    @staticmethod
    def _token_fingerprint(token: TokenData | None) -> str:
        if token is None or not token.refresh_token:
            return "missing"
        return hashlib.sha256(token.refresh_token.encode("utf-8")).hexdigest()[:10]

    @classmethod
    def _refresh_token_changed(
        cls,
        attempted: TokenData | None,
        latest: TokenData | None,
    ) -> bool:
        return (
            attempted is not None
            and latest is not None
            and bool(latest.refresh_token)
            and latest.refresh_token != attempted.refresh_token
        )

    @staticmethod
    def _reauthorization_error(exc: AuthError) -> AuthError:
        code = exc.code or "unknown"
        return AuthError(
            f"飞书刷新凭证已失效，请重新连接飞书（code={code}）",
            code=exc.code,
        )

    @classmethod
    def _get_refresh_lock(cls) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        with cls._refresh_locks_guard:
            lock = cls._refresh_locks.get(loop_id)
            if lock is None:
                lock = asyncio.Lock()
                cls._refresh_locks[loop_id] = lock
            return lock

    async def _fetch_open_id(self, access_token: str) -> str | None:
        profile = await self._fetch_user_profile(access_token)
        return profile.open_id

    async def _fetch_user_profile(self, access_token: str) -> UserProfile:
        """
        使用 authen 用户信息接口补齐用户身份。
        该接口在 token 响应不返回 open_id 时，仍可获取 open_id 与昵称。
        """
        if self._http_client is not None and not hasattr(self._http_client, "get"):
            return UserProfile()

        user_info_url = f"{open_base_url(self._brand)}/open-apis/authen/v1/user_info"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with self._get_client() as client:
                response = await client.get(user_info_url, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("补齐用户身份失败：{}", exc)
            return UserProfile()

        if not isinstance(payload, dict):
            return UserProfile()
        if payload.get("code") != 0:
            logger.warning(
                "补齐用户身份失败，user_info code={} msg={}",
                payload.get("code"),
                payload.get("msg"),
            )
            return UserProfile()

        data = payload.get("data")
        if not isinstance(data, dict):
            return UserProfile()
        open_id: str | None = None
        account_name: str | None = None
        open_id = data.get("open_id")
        if isinstance(open_id, str) and open_id.strip():
            open_id = open_id.strip()
        else:
            open_id = None
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            account_name = name.strip()
        return UserProfile(open_id=open_id, account_name=account_name)

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
                raise AuthError(f"{message} (code={code})", code=str(code))
            wrapped = data.get("data")
            if isinstance(wrapped, dict):
                data = wrapped

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        open_id_raw = data.get("open_id")

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
            open_id=open_id_raw.strip() if isinstance(open_id_raw, str) and open_id_raw.strip() else None,
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

    @staticmethod
    def _extract_error_code(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        code = payload.get("code")
        return str(code) if code is not None else None

    def _get_client(self) -> httpx.AsyncClient:
        return self._http_client or httpx.AsyncClient(timeout=15.0)
