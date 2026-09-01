from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from src.services.auth_session_service import AuthSessionService
from src.services.device_flow_service import (
    DeviceAuthorization,
    DevicePollResult,
    DeviceToken,
)


@dataclass
class _Profile:
    id: str = "profile-1"
    app_id: str = "cli_test"
    brand: str = "feishu"


class _Accounts:
    def __init__(self) -> None:
        self.saved = None

    async def get_app_profile_credentials(self, _profile_id: str):
        return _Profile(), "secret"

    async def upsert_account(self, **kwargs):
        self.saved = kwargs
        return type("Account", (), {"id": "account-1", "state": "connected"})()

    async def reauthorize_account(self, **kwargs):
        self.saved = kwargs
        return type("Account", (), {"id": kwargs["account_id"], "state": "connected"})()


class _DeviceProtocol:
    async def begin(self, **_kwargs):
        return DeviceAuthorization(
            device_code="private-device-code",
            user_code="ABCD-EFGH",
            verification_uri="https://example.test/verify",
            verification_uri_complete="https://example.test/verify?code=ABCD-EFGH",
            expires_in=300,
            interval=1,
        )

    async def poll_once(self, **_kwargs):
        return DevicePollResult(
            status="authorized",
            token=DeviceToken(
                access_token="access",
                refresh_token="refresh",
                expires_in=7200,
                refresh_expires_in=604800,
                scope="drive:drive offline_access",
            ),
        )


@pytest.mark.asyncio
async def test_device_session_finishes_and_persists_identity(monkeypatch) -> None:
    accounts = _Accounts()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {"open_id": "ou_1", "name": "测试用户"},
            },
        )
    )
    client = httpx.AsyncClient(transport=transport)
    service = AuthSessionService(
        account_service=accounts,  # type: ignore[arg-type]
        device_protocol=_DeviceProtocol(),  # type: ignore[arg-type]
        http_client=client,
        clock=lambda: 1000.0,
    )
    monkeypatch.setattr(
        "src.services.auth_session_service.account_runtime_registry.reload",
        lambda: _async_none(),
    )

    session = await service.begin_device("profile-1")
    assert session.device_code == "private-device-code"
    result = await service.poll_device(session.id)

    assert result["status"] == "authorized"
    assert accounts.saved["open_id"] == "ou_1"
    assert accounts.saved["token"].refresh_token == "refresh"
    assert accounts.saved["auth_protocol"] == "device_v2"
    assert (await service.poll_device(session.id))["status"] == "authorized"
    assert service.cancel(session.id) is True
    await client.aclose()


@pytest.mark.asyncio
async def test_reauthorize_session_updates_exact_target_account(monkeypatch) -> None:
    accounts = _Accounts()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            request=request,
            json={"code": 0, "data": {"open_id": "ou_1", "name": "测试用户"}},
        )
    )
    client = httpx.AsyncClient(transport=transport)
    service = AuthSessionService(
        account_service=accounts,  # type: ignore[arg-type]
        device_protocol=_DeviceProtocol(),  # type: ignore[arg-type]
        http_client=client,
        clock=lambda: 1000.0,
    )
    monkeypatch.setattr(
        "src.services.auth_session_service.account_runtime_registry.reload",
        lambda: _async_none(),
    )

    session = await service.begin_device("profile-1", target_account_id="account-existing")
    result = await service.poll_device(session.id)

    assert result["status"] == "authorized"
    assert accounts.saved["account_id"] == "account-existing"
    assert accounts.saved["token"].auth_protocol == "device_v2"
    await client.aclose()


async def _async_none() -> None:
    return None
