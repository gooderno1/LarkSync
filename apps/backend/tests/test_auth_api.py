import pytest

from src.api import auth as auth_api
from src.core.security import TokenData


@pytest.mark.asyncio
async def test_status_fills_account_name_when_missing(monkeypatch) -> None:
    class DummyAuthService:
        def __init__(self) -> None:
            self._token = TokenData(
                access_token="token",
                refresh_token="refresh",
                expires_at=123.0,
                open_id="ou-test",
                account_name=None,
            )

        def get_cached_token(self) -> TokenData | None:
            return self._token

        async def ensure_cached_identity(self) -> TokenData | None:
            self._token = TokenData(
                access_token="token",
                refresh_token="refresh",
                expires_at=123.0,
                open_id="ou-test",
                account_name="测试用户",
            )
            return self._token

        async def get_valid_access_token(self) -> str:
            return "token"

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)
    monkeypatch.setattr(auth_api, "current_device_id", lambda: "dev-test")

    async def fake_check_drive_permission(_access_token: str) -> bool:
        return True

    monkeypatch.setattr(auth_api, "_check_drive_permission", fake_check_drive_permission)

    payload = await auth_api.status()
    assert payload["connected"] is True
    assert payload["open_id"] == "ou-test"
    assert payload["account_name"] == "测试用户"
    assert payload["device_id"] == "dev-test"
    assert payload["drive_ok"] is True
