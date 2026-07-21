import pytest
from starlette.requests import Request

from src.api import auth as auth_api
from src.services import AuthError
from src.core.security import TokenData
from src.services.lark_cli_auth_service import LarkCliAuthStatus


@pytest.mark.asyncio
async def test_status_is_a_local_binary_check_without_remote_work(monkeypatch) -> None:
    calls: list[str] = []

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
            calls.append("identity")
            raise AssertionError("状态检查不应请求用户信息")

        async def get_valid_access_token(self) -> str:
            calls.append("refresh")
            raise AssertionError("状态检查不应刷新 token")

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)
    monkeypatch.setattr(auth_api, "current_device_id", lambda: "dev-test")

    payload = await auth_api.status()
    assert payload["connected"] is True
    assert payload["open_id"] == "ou-test"
    assert payload["account_name"] is None
    assert payload["device_id"] == "dev-test"
    assert "drive_ok" not in payload
    assert "drive_check_error" not in payload
    assert calls == []


@pytest.mark.asyncio
async def test_status_reports_unauthorized_only_when_local_token_is_missing(monkeypatch) -> None:
    class DummyAuthService:
        def get_cached_token(self) -> None:
            return None

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)
    monkeypatch.setattr(auth_api, "current_device_id", lambda: "dev-test")

    payload = await auth_api.status()

    assert payload["connected"] is False
    assert payload["expires_at"] is None


@pytest.mark.asyncio
async def test_callback_triggers_update_check_on_login(monkeypatch) -> None:
    class DummyAuthService:
        async def exchange_code(self, _code: str) -> TokenData:
            return TokenData(
                access_token="token",
                refresh_token="refresh",
                expires_at=123.0,
                open_id="ou-test",
                account_name="测试用户",
            )

    called = {"update": False, "identity": False}

    def fake_schedule(_request: Request) -> None:
        called["update"] = True

    def fake_identity_schedule(_auth_service: DummyAuthService) -> None:
        called["identity"] = True

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)
    monkeypatch.setattr(auth_api, "_schedule_login_update_check", fake_schedule)
    monkeypatch.setattr(auth_api, "_schedule_identity_hydration", fake_identity_schedule)

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/callback",
            "headers": [],
            "query_string": b"",
            "app": object(),
        }
    )
    payload = await auth_api.callback(request=request, code="abc", state=None)

    assert payload["connected"] is True
    assert called == {"update": True, "identity": True}


@pytest.mark.asyncio
async def test_authorize_url_returns_json_url_and_state(monkeypatch) -> None:
    class DummyAuthService:
        def build_authorize_url(self, state: str) -> str:
            return (
                "https://open.feishu.cn/oauth?"
                f"redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fauth%2Fcallback&state={state}"
            )

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)
    monkeypatch.setattr(auth_api.state_store, "issue", lambda redirect: "state-json")

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/authorize-url",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "query_string": b"",
            "app": object(),
        }
    )

    payload = await auth_api.authorize_url(
        request=request,
        state=None,
        redirect="http://127.0.0.1:3666",
    )

    assert payload["authorize_url"] == (
        "https://open.feishu.cn/oauth?"
        "redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fauth%2Fcallback&state=state-json"
    )
    assert payload["state"] == "state-json"
    assert payload["expires_in"] == auth_api.state_store.ttl_seconds
    assert payload["local_callback"] is True


@pytest.mark.asyncio
async def test_authorize_url_rejects_missing_config(monkeypatch) -> None:
    class DummyAuthService:
        def build_authorize_url(self, _state: str) -> str:
            raise AuthError("auth_client_id 未配置")

    monkeypatch.setattr(auth_api, "AuthService", DummyAuthService)

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/authorize-url",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "query_string": b"",
            "app": object(),
        }
    )

    with pytest.raises(auth_api.HTTPException) as excinfo:
        await auth_api.authorize_url(request=request, state=None, redirect=None)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "auth_client_id 未配置"


@pytest.mark.asyncio
async def test_cli_status_returns_lark_cli_probe(monkeypatch) -> None:
    def fake_status() -> LarkCliAuthStatus:
        return LarkCliAuthStatus(
            installed=True,
            executable="lark-cli.cmd",
            message="lark-cli 用户身份可用",
            can_assist_oauth=True,
        )

    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(auth_api, "get_lark_cli_auth_status", fake_status)
    monkeypatch.setattr(auth_api.asyncio, "to_thread", fake_to_thread)

    payload = await auth_api.cli_status()

    assert payload.installed is True
    assert payload.executable == "lark-cli.cmd"
    assert payload.can_assist_oauth is True
