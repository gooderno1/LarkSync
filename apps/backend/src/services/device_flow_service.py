from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

import httpx


Brand = Literal["feishu", "lark"]


class DeviceFlowProtocolError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


def normalize_brand(value: str | None) -> Brand:
    return "lark" if (value or "").strip().lower() == "lark" else "feishu"


def open_base_url(brand: str | None) -> str:
    return (
        "https://open.larksuite.com"
        if normalize_brand(brand) == "lark"
        else "https://open.feishu.cn"
    )


def accounts_base_url(brand: str | None) -> str:
    return (
        "https://accounts.larksuite.com"
        if normalize_brand(brand) == "lark"
        else "https://accounts.feishu.cn"
    )


@dataclass(frozen=True)
class DeviceAuthorization:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


@dataclass(frozen=True)
class DeviceToken:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    scope: str


@dataclass(frozen=True)
class DevicePollResult:
    status: Literal["pending", "slow_down", "authorized", "denied", "expired"]
    token: DeviceToken | None = None
    message: str | None = None


class DeviceFlowProtocol:
    """Port of the official lark-cli Device Flow HTTP contract.

    Source: github.com/larksuite/cli/internal/auth/device_flow.go (v1.0.92).
    The protocol is implemented in-process; LarkSync never shells out to lark-cli.
    """

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def begin(
        self,
        *,
        app_id: str,
        app_secret: str,
        brand: str,
        scopes: list[str],
    ) -> DeviceAuthorization:
        requested = [scope.strip() for scope in scopes if scope.strip()]
        if "offline_access" not in requested:
            requested.append("offline_access")
        endpoint = f"{accounts_base_url(brand)}/oauth/v1/device_authorization"
        async with self._client() as client:
            response = await client.post(
                endpoint,
                content=urlencode({"client_id": app_id, "scope": " ".join(requested)}),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=httpx.BasicAuth(app_id, app_secret),
            )
        payload = self._json_object(response, operation="Device authorization")
        self._raise_protocol_error(response, payload, operation="Device authorization")
        device_code = self._required_string(payload, "device_code")
        verification_uri = self._required_string(payload, "verification_uri")
        verification_complete = self._optional_string(
            payload, "verification_uri_complete"
        ) or verification_uri
        return DeviceAuthorization(
            device_code=device_code,
            user_code=self._optional_string(payload, "user_code") or "",
            verification_uri=verification_uri,
            verification_uri_complete=verification_complete,
            expires_in=self._integer(payload, "expires_in", 240),
            interval=max(1, self._integer(payload, "interval", 5)),
        )

    async def poll_once(
        self,
        *,
        app_id: str,
        app_secret: str,
        brand: str,
        device_code: str,
    ) -> DevicePollResult:
        endpoint = f"{open_base_url(brand)}/open-apis/authen/v2/oauth/token"
        form = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": app_id,
            "client_secret": app_secret,
        }
        async with self._client() as client:
            response = await client.post(
                endpoint,
                content=urlencode(form),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        payload = self._json_object(response, operation="Device token")
        error = self._optional_string(payload, "error")
        if not error and self._optional_string(payload, "access_token"):
            token_expires = self._integer(payload, "expires_in", 7200)
            refresh_token = self._optional_string(payload, "refresh_token") or ""
            return DevicePollResult(
                status="authorized",
                token=DeviceToken(
                    access_token=self._required_string(payload, "access_token"),
                    refresh_token=refresh_token,
                    expires_in=token_expires,
                    refresh_expires_in=self._integer(
                        payload,
                        "refresh_token_expires_in",
                        604800 if refresh_token else token_expires,
                    ),
                    scope=self._optional_string(payload, "scope") or "",
                ),
            )
        if error == "authorization_pending":
            return DevicePollResult(status="pending")
        if error == "slow_down":
            return DevicePollResult(status="slow_down")
        if error == "access_denied":
            return DevicePollResult(
                status="denied",
                message=self._optional_string(payload, "error_description"),
            )
        if error in {"expired_token", "invalid_grant"}:
            return DevicePollResult(
                status="expired",
                message=self._optional_string(payload, "error_description"),
            )
        message = self._optional_string(payload, "error_description") or error
        if not message:
            message = f"HTTP {response.status_code}"
        raise DeviceFlowProtocolError(
            f"Device token failed: {error or 'unknown_error'}: {message}",
            code=error,
        )

    def _client(self):
        if self._http_client is not None:
            return _BorrowedAsyncClient(self._http_client)
        return httpx.AsyncClient(timeout=30.0)

    @staticmethod
    def _json_object(response: httpx.Response, *, operation: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise DeviceFlowProtocolError(
                f"{operation} failed: response is not JSON (HTTP {response.status_code})"
            ) from exc
        if not isinstance(payload, dict):
            raise DeviceFlowProtocolError(f"{operation} failed: invalid JSON object")
        return payload

    @classmethod
    def _raise_protocol_error(
        cls,
        response: httpx.Response,
        payload: dict[str, Any],
        *,
        operation: str,
    ) -> None:
        error = cls._optional_string(payload, "error")
        if response.status_code < 400 and not error:
            return
        message = cls._optional_string(payload, "error_description") or error
        raise DeviceFlowProtocolError(
            f"{operation} failed: {message or f'HTTP {response.status_code}'}",
            code=error,
        )

    @staticmethod
    def _optional_string(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @classmethod
    def _required_string(cls, payload: dict[str, Any], key: str) -> str:
        value = cls._optional_string(payload, key)
        if value is None:
            raise DeviceFlowProtocolError(f"Protocol response missing {key}")
        return value

    @staticmethod
    def _integer(payload: dict[str, Any], key: str, default: int) -> int:
        value = payload.get(key)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return int(value)
        return default


@dataclass(frozen=True)
class AppRegistrationAuthorization:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int
    brand: Brand


@dataclass(frozen=True)
class AppRegistrationPollResult:
    status: Literal["pending", "slow_down", "registered", "denied", "expired", "brand_switched"]
    brand: Brand
    app_id: str | None = None
    app_secret: str | None = None
    open_id: str | None = None
    message: str | None = None


class AppRegistrationProtocol(DeviceFlowProtocol):
    async def begin(self, *, brand: str) -> AppRegistrationAuthorization:
        selected_brand = normalize_brand(brand)
        endpoint = f"{accounts_base_url('feishu')}/oauth/v1/app/registration"
        form = {
            "action": "begin",
            "archetype": "PersonalAgent",
            "auth_method": "client_secret",
            "request_user_info": "open_id tenant_brand",
        }
        async with self._client() as client:
            response = await client.post(
                endpoint,
                content=urlencode(form),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        payload = self._json_object(response, operation="App registration")
        self._raise_protocol_error(response, payload, operation="App registration")
        device_code = self._required_string(payload, "device_code")
        user_code = self._optional_string(payload, "user_code") or ""
        verification_uri = self._optional_string(payload, "verification_uri") or ""
        complete = f"{open_base_url(selected_brand)}/page/cli?user_code={user_code}"
        return AppRegistrationAuthorization(
            device_code=device_code,
            user_code=user_code,
            verification_uri=verification_uri,
            verification_uri_complete=complete,
            expires_in=self._integer(
                payload,
                "expire_in",
                self._integer(payload, "expires_in", 600),
            ),
            interval=max(1, self._integer(payload, "interval", 5)),
            brand=selected_brand,
        )

    async def poll_once(
        self,
        *,
        brand: str,
        device_code: str,
    ) -> AppRegistrationPollResult:
        selected_brand = normalize_brand(brand)
        endpoint = f"{accounts_base_url(selected_brand)}/oauth/v1/app/registration"
        async with self._client() as client:
            response = await client.post(
                endpoint,
                content=urlencode({"action": "poll", "device_code": device_code}),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        payload = self._json_object(response, operation="App registration poll")
        user_info = payload.get("user_info")
        if not isinstance(user_info, dict):
            user_info = {}
        tenant_brand = normalize_brand(self._optional_string(user_info, "tenant_brand"))
        if tenant_brand != selected_brand:
            return AppRegistrationPollResult(
                status="brand_switched",
                brand=tenant_brand,
            )
        error = self._optional_string(payload, "error")
        app_id = self._optional_string(payload, "client_id")
        app_secret = self._optional_string(payload, "client_secret")
        if not error and app_id and app_secret:
            return AppRegistrationPollResult(
                status="registered",
                brand=selected_brand,
                app_id=app_id,
                app_secret=app_secret,
                open_id=self._optional_string(user_info, "open_id"),
            )
        if not error or error == "authorization_pending":
            return AppRegistrationPollResult(status="pending", brand=selected_brand)
        if error == "slow_down":
            return AppRegistrationPollResult(status="slow_down", brand=selected_brand)
        if error == "access_denied":
            return AppRegistrationPollResult(status="denied", brand=selected_brand)
        if error in {"expired_token", "invalid_grant"}:
            return AppRegistrationPollResult(status="expired", brand=selected_brand)
        raise DeviceFlowProtocolError(
            f"App registration poll failed: {self._optional_string(payload, 'error_description') or error}",
            code=error,
        )


class _BorrowedAsyncClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *_args: object) -> None:
        return None


__all__ = [
    "AppRegistrationAuthorization",
    "AppRegistrationPollResult",
    "AppRegistrationProtocol",
    "DeviceAuthorization",
    "DeviceFlowProtocol",
    "DeviceFlowProtocolError",
    "DevicePollResult",
    "DeviceToken",
    "accounts_base_url",
    "normalize_brand",
    "open_base_url",
]
