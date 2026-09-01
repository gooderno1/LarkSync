from __future__ import annotations

import httpx
import pytest

from src.services.device_flow_service import (
    DeviceFlowProtocol,
    DeviceFlowProtocolError,
)


@pytest.mark.asyncio
async def test_device_flow_begin_uses_official_protocol_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/oauth/v1/device_authorization"
        assert request.headers["authorization"].startswith("Basic ")
        body = request.content.decode()
        assert "client_id=cli_test" in body
        assert "offline_access" in body
        return httpx.Response(
            200,
            json={
                "device_code": "device-1",
                "user_code": "ABCD-EFGH",
                "verification_uri": "https://open.feishu.cn/device",
                "verification_uri_complete": "https://open.feishu.cn/device?code=ABCD-EFGH",
                "expires_in": 240,
                "interval": 5,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        protocol = DeviceFlowProtocol(http_client=client)
        result = await protocol.begin(
            app_id="cli_test",
            app_secret="secret",
            brand="feishu",
            scopes=["drive:drive"],
        )

    assert result.device_code == "device-1"
    assert result.user_code == "ABCD-EFGH"
    assert result.interval == 5


@pytest.mark.asyncio
async def test_device_flow_poll_handles_pending_slow_down_and_success() -> None:
    responses = iter(
        [
            {"error": "authorization_pending"},
            {"error": "slow_down"},
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 7200,
                "refresh_token_expires_in": 604800,
                "scope": "drive:drive offline_access",
            },
        ]
    )

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(responses))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        protocol = DeviceFlowProtocol(http_client=client)
        pending = await protocol.poll_once(
            app_id="cli_test", app_secret="secret", brand="feishu", device_code="d"
        )
        slowed = await protocol.poll_once(
            app_id="cli_test", app_secret="secret", brand="feishu", device_code="d"
        )
        success = await protocol.poll_once(
            app_id="cli_test", app_secret="secret", brand="feishu", device_code="d"
        )

    assert pending.status == "pending"
    assert slowed.status == "slow_down"
    assert success.status == "authorized"
    assert success.token is not None
    assert success.token.refresh_token == "refresh"


@pytest.mark.asyncio
async def test_device_flow_rejects_unknown_error_without_logging_secrets() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_client", "error_description": "bad"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        protocol = DeviceFlowProtocol(http_client=client)
        with pytest.raises(DeviceFlowProtocolError, match="invalid_client"):
            await protocol.poll_once(
                app_id="cli_test", app_secret="secret", brand="feishu", device_code="d"
            )
