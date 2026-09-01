from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from src.core.security import CredentialStorageError
from src.services.auth_session_service import AuthSessionService
from src.services.device_flow_service import (
    AppRegistrationAuthorization,
    AppRegistrationPollResult,
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

    async def create_app_profile(self, **kwargs):
        self.saved = kwargs
        return type(
            "AppProfile",
            (),
            {
                "id": "profile-created",
                "app_id": kwargs["app_id"],
                "brand": kwargs["brand"],
                "display_name": kwargs["display_name"],
            },
        )()


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


class _RegistrationProtocol:
    async def begin(self, **_kwargs):
        return AppRegistrationAuthorization(
            device_code="registration-code",
            user_code="REG-1",
            verification_uri="https://example.test/register",
            verification_uri_complete="https://example.test/register?code=REG-1",
            expires_in=300,
            interval=1,
            brand="feishu",
        )

    async def poll_once(self, **_kwargs):
        return AppRegistrationPollResult(
            status="registered",
            brand="feishu",
            app_id="cli_created",
            app_secret="created-secret",
        )


@pytest.mark.asyncio
async def test_registration_stops_at_explicit_success_checkpoint() -> None:
    accounts = _Accounts()
    service = AuthSessionService(
        account_service=accounts,  # type: ignore[arg-type]
        device_protocol=_DeviceProtocol(),  # type: ignore[arg-type]
        registration_protocol=_RegistrationProtocol(),  # type: ignore[arg-type]
        clock=lambda: 1000.0,
    )

    session = await service.begin_registration("feishu")
    result = await service.poll_registration(session.id)

    assert result["status"] == "registered"
    assert result["app_profile"].id == "profile-created"
    assert "next_session" not in result
    assert accounts.saved["display_name"] == "LarkSync"
    assert await service.poll_registration(session.id) == result

@pytest.mark.asyncio
async def test_device_session_finishes_and_persists_identity(monkeypatch) -> None:
    accounts = _Accounts()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {
                    "open_id": "ou_1",
                    "name": "测试用户",
                    "tenant_key": "tenant_alpha",
                },
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
    assert accounts.saved["tenant_key"] == "tenant_alpha"
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
            json={
                "code": 0,
                "data": {
                    "open_id": "ou_1",
                    "name": "测试用户",
                    "tenant_key": "tenant_alpha",
                },
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

    session = await service.begin_device("profile-1", target_account_id="account-existing")
    result = await service.poll_device(session.id)

    assert result["status"] == "authorized"
    assert accounts.saved["account_id"] == "account-existing"
    assert accounts.saved["tenant_key"] == "tenant_alpha"
    assert accounts.saved["token"].auth_protocol == "device_v2"
    await client.aclose()


@pytest.mark.asyncio
async def test_reauthorize_session_returns_stable_storage_failure(monkeypatch) -> None:
    class FailingAccounts(_Accounts):
        async def reauthorize_account(self, **kwargs):
            self.saved = kwargs
            raise CredentialStorageError("Windows 凭据管理器拒绝保存新凭据")

    accounts = FailingAccounts()
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

    session = await service.begin_device(
        "profile-1", target_account_id="account-existing"
    )
    result = await service.poll_device(session.id)

    assert result == {
        "status": "credential_storage_failed",
        "message": (
            "飞书授权已完成，但新凭据未能安全保存。原授权仍保留，"
            "请重新开始授权；如果持续出现，请检查 Windows 凭据管理器。"
        ),
    }
    assert await service.poll_device(session.id) == result
    await client.aclose()


@pytest.mark.asyncio
async def test_saved_authorization_stays_successful_when_runtime_reload_is_deferred(
    monkeypatch,
) -> None:
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

    async def fail_reload() -> None:
        raise RuntimeError("runtime reload failed")

    monkeypatch.setattr(
        "src.services.auth_session_service.account_runtime_registry.reload",
        fail_reload,
    )

    session = await service.begin_device("profile-1")
    result = await service.poll_device(session.id)

    assert result["status"] == "authorized"
    assert result["runtime_reload_pending"] is True
    assert await service.poll_device(session.id) == result
    await client.aclose()


async def _async_none() -> None:
    return None
