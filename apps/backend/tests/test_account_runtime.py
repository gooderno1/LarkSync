from __future__ import annotations

from src.services.account_runtime import AccountRuntime


def test_account_runtime_routes_legacy_and_device_tokens_to_matching_endpoints() -> None:
    legacy = AccountRuntime(
        account_id="legacy",
        brand="feishu",
        app_id="cli_legacy",
        app_secret="secret",
        auth_protocol="legacy_v1",
    )
    device = AccountRuntime(
        account_id="device",
        brand="feishu",
        app_id="cli_device",
        app_secret="secret",
        auth_protocol="device_v2",
    )

    assert legacy.app_config().auth_token_url.endswith("/authen/v1/access_token")
    assert device.app_config().auth_token_url.endswith("/authen/v2/oauth/token")
