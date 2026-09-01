from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Callable

import httpx

from src.core.config import ConfigManager
from src.core.security import TokenData
from src.services.account_runtime import account_runtime_registry
from src.services.account_service import AccountService
from src.services.device_flow_service import (
    AppRegistrationProtocol,
    DeviceFlowProtocol,
    open_base_url,
)


@dataclass
class PendingSession:
    id: str
    kind: str
    device_code: str
    brand: str
    expires_at: float
    interval: int
    next_poll_at: float
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    app_profile_id: str | None = None
    scopes: list[str] | None = None
    target_account_id: str | None = None
    terminal_result: dict[str, object] | None = None


class AuthSessionService:
    """管理短生命周期授权会话；device_code 只存在于进程内存。"""

    def __init__(
        self,
        *,
        account_service: AccountService | None = None,
        device_protocol: DeviceFlowProtocol | None = None,
        registration_protocol: AppRegistrationProtocol | None = None,
        http_client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._accounts = account_service or AccountService()
        self._device = device_protocol or DeviceFlowProtocol(http_client)
        self._registration = registration_protocol or AppRegistrationProtocol(http_client)
        self._http_client = http_client
        self._clock = clock
        self._sessions: dict[str, PendingSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def begin_device(
        self, app_profile_id: str, *, target_account_id: str | None = None
    ) -> PendingSession:
        profile, secret = await self._accounts.get_app_profile_credentials(
            app_profile_id
        )
        scopes = list(ConfigManager.get().config.auth_scopes)
        authorization = await self._device.begin(
            app_id=profile.app_id,
            app_secret=secret,
            brand=profile.brand,
            scopes=scopes,
        )
        return self._put(
            kind="device",
            authorization=authorization,
            brand=profile.brand,
            app_profile_id=profile.id,
            scopes=scopes,
            target_account_id=target_account_id,
        )

    async def poll_device(self, session_id: str) -> dict[str, object]:
        session = self._require(session_id, "device")
        async with self._lock(session_id):
            if session.terminal_result is not None:
                return session.terminal_result
            now = self._clock()
            if now >= session.expires_at:
                self.cancel(session_id)
                return {"status": "expired"}
            if now < session.next_poll_at:
                return {
                    "status": "pending",
                    "retry_after": max(1, int(session.next_poll_at - now)),
                }
            profile, secret = await self._accounts.get_app_profile_credentials(
                session.app_profile_id or ""
            )
            result = await self._device.poll_once(
                app_id=profile.app_id,
                app_secret=secret,
                brand=session.brand,
                device_code=session.device_code,
            )
            if result.status == "slow_down":
                session.interval += 5
            session.next_poll_at = now + session.interval
            if result.status != "authorized" or result.token is None:
                if result.status in {"denied", "expired"}:
                    self.cancel(session_id)
                return {"status": result.status, "message": result.message}
            profile_data = await self._fetch_user_profile(
                brand=session.brand,
                access_token=result.token.access_token,
            )
            open_id = str(profile_data.get("open_id") or "").strip()
            if not open_id:
                raise ValueError("授权成功，但用户信息响应缺少 open_id")
            token = TokenData(
                access_token=result.token.access_token,
                refresh_token=result.token.refresh_token,
                expires_at=now + result.token.expires_in,
                open_id=open_id,
                account_name=str(profile_data.get("name") or "").strip() or None,
                scope=result.token.scope,
                refresh_expires_at=now + result.token.refresh_expires_in,
                auth_protocol="device_v2",
            )
            account_payload = {
                "app_profile_id": profile.id,
                "open_id": open_id,
                "account_name": token.account_name,
                "granted_scopes": (result.token.scope.split() or session.scopes or []),
                "token": token,
                "avatar_url": str(profile_data.get("avatar_url") or "").strip() or None,
                "tenant_name": str(profile_data.get("tenant_name") or "").strip() or None,
            }
            if session.target_account_id:
                account = await self._accounts.reauthorize_account(
                    account_id=session.target_account_id,
                    **account_payload,
                )
            else:
                account = await self._accounts.upsert_account(
                    auth_protocol="device_v2",
                    **account_payload,
                )
            await account_runtime_registry.reload()
            session.terminal_result = {"status": "authorized", "account": account}
            return session.terminal_result

    async def begin_registration(self, brand: str) -> PendingSession:
        authorization = await self._registration.begin(brand=brand)
        return self._put(
            kind="registration",
            authorization=authorization,
            brand=authorization.brand,
        )

    async def poll_registration(self, session_id: str) -> dict[str, object]:
        session = self._require(session_id, "registration")
        async with self._lock(session_id):
            if session.terminal_result is not None:
                return session.terminal_result
            now = self._clock()
            if now >= session.expires_at:
                self.cancel(session_id)
                return {"status": "expired"}
            if now < session.next_poll_at:
                return {
                    "status": "pending",
                    "retry_after": max(1, int(session.next_poll_at - now)),
                }
            result = await self._registration.poll_once(
                brand=session.brand,
                device_code=session.device_code,
            )
            if result.status == "slow_down":
                session.interval += 5
            session.next_poll_at = now + session.interval
            if result.status == "brand_switched":
                session.brand = result.brand
                return {"status": result.status, "brand": result.brand}
            if result.status != "registered":
                if result.status in {"denied", "expired"}:
                    self.cancel(session_id)
                return {"status": result.status, "message": result.message}
            profile = await self._accounts.create_app_profile(
                app_id=result.app_id or "",
                app_secret=result.app_secret or "",
                brand=result.brand,
                source="official_registration",
                display_name="LarkSync 自动创建的个人应用",
            )
            next_session = await self.begin_device(profile.id)
            session.terminal_result = {
                "status": "registered",
                "app_profile": profile,
                "next_session": self._public_session(next_session),
            }
            return session.terminal_result

    def cancel(self, session_id: str) -> bool:
        removed = self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)
        return removed is not None

    def _put(
        self,
        *,
        kind: str,
        authorization,
        brand: str,
        app_profile_id: str | None = None,
        scopes: list[str] | None = None,
        target_account_id: str | None = None,
    ) -> PendingSession:
        now = self._clock()
        item = PendingSession(
            id=str(uuid.uuid4()),
            kind=kind,
            device_code=authorization.device_code,
            brand=brand,
            expires_at=now + authorization.expires_in,
            interval=authorization.interval,
            next_poll_at=now,
            user_code=authorization.user_code,
            verification_uri=authorization.verification_uri,
            verification_uri_complete=authorization.verification_uri_complete,
            app_profile_id=app_profile_id,
            scopes=scopes,
            target_account_id=target_account_id,
        )
        self._sessions[item.id] = item
        return item

    @staticmethod
    def _public_session(session: PendingSession) -> dict[str, object]:
        return {
            "session_id": session.id,
            "status": "pending",
            "brand": session.brand,
            "user_code": session.user_code,
            "verification_uri": session.verification_uri,
            "verification_uri_complete": session.verification_uri_complete,
            "expires_at": session.expires_at,
            "interval": session.interval,
        }

    def _require(self, session_id: str, kind: str) -> PendingSession:
        session = self._sessions.get(session_id)
        if session is None or session.kind != kind:
            raise ValueError("授权会话不存在或已结束")
        return session

    def _lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    async def _fetch_user_profile(
        self, *, brand: str, access_token: str
    ) -> dict[str, object]:
        endpoint = f"{open_base_url(brand)}/open-apis/authen/v1/user_info"
        client = self._http_client or httpx.AsyncClient(timeout=30.0)
        should_close = self._http_client is None
        try:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if should_close:
                await client.aclose()
        if not isinstance(payload, dict) or payload.get("code") != 0:
            raise ValueError("用户信息读取失败")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("用户信息响应格式无效")
        return data


__all__ = ["AuthSessionService", "PendingSession"]
