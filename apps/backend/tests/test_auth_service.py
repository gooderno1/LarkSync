import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.core.config import AppConfig
from src.core.security import MemoryTokenStore, TokenData
from src.services.auth_service import AuthError, AuthService


class FakeAsyncClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        exc: Exception | None = None,
        get_response: httpx.Response | None = None,
        get_exc: Exception | None = None,
    ):
        self._response = response
        self._exc = exc
        self._get_response = get_response
        self._get_exc = get_exc
        self.get_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict[str, str]):
        if self._exc:
            raise self._exc
        return self._response

    async def get(self, url: str, headers: dict[str, str] | None = None):
        self.get_calls += 1
        if self._get_exc:
            raise self._get_exc
        return self._get_response


class SequencedRefreshClient:
    def __init__(self, responses: list[httpx.Response], delay: float = 0.0):
        self._responses = responses
        self._delay = delay
        self.post_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict[str, str]):
        self.post_calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if not self._responses:
            raise AssertionError("unexpected refresh call")
        return self._responses.pop(0)

    async def get(self, url: str, headers: dict[str, str] | None = None):
        return httpx.Response(
            200,
            json={"code": 0, "data": {"open_id": "ou-test-user", "name": "测试用户"}},
            request=httpx.Request("GET", url),
        )


def test_build_authorize_url() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
        auth_scopes=["scope.read", "scope.write"],
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())
    url = service.build_authorize_url("state-xyz")
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    params = parse_qs(parsed.query)
    assert params["app_id"] == ["client-123"]
    assert params["redirect_uri"] == ["http://localhost/callback"]
    assert params["state"] == ["state-xyz"]


@pytest.mark.asyncio
async def test_exchange_code_requires_app_credentials() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())

    with pytest.raises(AuthError):
        await service.exchange_code("code-123")

    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="",
        auth_redirect_uri="http://localhost/callback",
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())

    with pytest.raises(AuthError):
        await service.exchange_code("code-456")


@pytest.mark.asyncio
async def test_refresh_requires_app_credentials() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="",
        auth_redirect_uri="http://localhost/callback",
    )
    store = MemoryTokenStore()
    store.set(TokenData(access_token="a", refresh_token="r", expires_at=None))
    service = AuthService(config=config, token_store=store)

    with pytest.raises(AuthError):
        await service.refresh()


@pytest.mark.asyncio
async def test_exchange_code_handles_http_error() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    request = httpx.Request("POST", "https://example.com/oauth/token")
    response = httpx.Response(
        400,
        json={"code": 20025, "msg": "missing app id or app secret"},
        request=request,
    )
    client = FakeAsyncClient(response=response)
    service = AuthService(config=config, token_store=MemoryTokenStore(), http_client=client)

    with pytest.raises(AuthError) as excinfo:
        await service.exchange_code("code-123")

    assert "missing app id" in str(excinfo.value)


@pytest.mark.asyncio
async def test_exchange_code_handles_request_error() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    request = httpx.Request("POST", "https://example.com/oauth/token")
    exc = httpx.RequestError("boom", request=request)
    client = FakeAsyncClient(exc=exc)
    service = AuthService(config=config, token_store=MemoryTokenStore(), http_client=client)

    with pytest.raises(AuthError) as excinfo:
        await service.exchange_code("code-123")

    assert "Token 请求失败" in str(excinfo.value)


@pytest.mark.asyncio
async def test_exchange_code_handles_non_json_response() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    request = httpx.Request("POST", "https://example.com/oauth/token")
    response = httpx.Response(200, content=b"not-json", request=request)
    client = FakeAsyncClient(response=response)
    service = AuthService(config=config, token_store=MemoryTokenStore(), http_client=client)

    with pytest.raises(AuthError) as excinfo:
        await service.exchange_code("code-123")

    assert "Token 响应不是 JSON" in str(excinfo.value)


def test_parse_token_response_missing_fields() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())

    with pytest.raises(AuthError):
        service._parse_token_response({})


def test_parse_token_response_wrapped_data() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())

    payload = {
        "code": 0,
        "msg": "success",
        "data": {
            "access_token": "token-123",
            "refresh_token": "refresh-456",
            "expires_in": 3600,
        },
    }
    token = service._parse_token_response(payload)
    assert token.access_token == "token-123"
    assert token.refresh_token == "refresh-456"


def test_parse_token_response_missing_refresh_token() -> None:
    """飞书 v2 端点可能不返回 refresh_token，应仍解析成功。"""
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    service = AuthService(config=config, token_store=MemoryTokenStore())

    # 没有 refresh_token 字段
    payload_no_field = {
        "access_token": "token-abc",
        "expires_in": 7200,
    }
    token = service._parse_token_response(payload_no_field)
    assert token.access_token == "token-abc"
    assert token.refresh_token == ""
    assert token.expires_in == 7200

    # refresh_token 为空字符串
    payload_empty = {
        "access_token": "token-def",
        "refresh_token": "",
        "expires_in": 3600,
    }
    token2 = service._parse_token_response(payload_empty)
    assert token2.access_token == "token-def"
    assert token2.refresh_token == ""


@pytest.mark.asyncio
async def test_refresh_fails_without_refresh_token() -> None:
    """当 refresh_token 为空时，refresh() 应抛出 AuthError。"""
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    store = MemoryTokenStore()
    store.set(TokenData(access_token="a", refresh_token="", expires_at=None))
    service = AuthService(config=config, token_store=store)

    with pytest.raises(AuthError, match="refresh_token 不可用"):
        await service.refresh()


@pytest.mark.asyncio
async def test_refresh_preserves_previous_refresh_token_when_response_omits_new_value() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    request = httpx.Request("POST", "https://example.com/oauth/token")
    response = httpx.Response(
        200,
        json={
            "code": 0,
            "data": {
                "access_token": "token-new",
                "expires_in": 3600,
                "open_id": "ou-test-user",
            },
        },
        request=request,
    )
    store = MemoryTokenStore()
    store.set(
        TokenData(
            access_token="token-old",
            refresh_token="refresh-old",
            expires_at=0,
            open_id="ou-test-user",
            account_name="测试用户",
        )
    )
    service = AuthService(
        config=config,
        token_store=store,
        http_client=FakeAsyncClient(response=response),
    )

    token = await service.refresh()

    assert token.access_token == "token-new"
    assert token.refresh_token == "refresh-old"
    stored = store.get()
    assert stored is not None
    assert stored.refresh_token == "refresh-old"


@pytest.mark.asyncio
async def test_get_valid_access_token_serializes_concurrent_refresh() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    request = httpx.Request("POST", "https://example.com/oauth/token")
    response = httpx.Response(
        200,
        json={
            "code": 0,
            "data": {
                "access_token": "token-new",
                "refresh_token": "refresh-new",
                "expires_in": 3600,
                "open_id": "ou-test-user",
            },
        },
        request=request,
    )
    store = MemoryTokenStore()
    store.set(
        TokenData(
            access_token="token-old",
            refresh_token="refresh-old",
            expires_at=0,
            open_id="ou-test-user",
            account_name="测试用户",
        )
    )
    client = SequencedRefreshClient([response], delay=0.05)
    service_a = AuthService(config=config, token_store=store, http_client=client)
    service_b = AuthService(config=config, token_store=store, http_client=client)

    results = await asyncio.gather(
        service_a.get_valid_access_token(),
        service_b.get_valid_access_token(),
    )

    assert results == ["token-new", "token-new"]
    assert client.post_calls == 1


@pytest.mark.asyncio
async def test_exchange_code_does_not_block_redirect_on_user_info() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    token_request = httpx.Request("POST", "https://example.com/oauth/token")
    user_info_request = httpx.Request(
        "GET", "https://open.feishu.cn/open-apis/authen/v1/user_info"
    )
    token_response = httpx.Response(
        200,
        json={
            "code": 0,
            "data": {
                "access_token": "token-123",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
            },
        },
        request=token_request,
    )
    user_info_response = httpx.Response(
        200,
        json={
            "code": 0,
            "data": {
                "open_id": "ou-test-user",
                "name": "测试用户",
            },
        },
        request=user_info_request,
    )
    store = MemoryTokenStore()
    client = FakeAsyncClient(response=token_response, get_response=user_info_response)
    service = AuthService(config=config, token_store=store, http_client=client)

    token = await service.exchange_code("code-123")
    assert token.open_id is None
    assert token.account_name is None
    assert client.get_calls == 0


@pytest.mark.asyncio
async def test_ensure_cached_identity_fetches_open_id() -> None:
    config = AppConfig(
        auth_authorize_url="https://example.com/oauth/authorize",
        auth_token_url="https://example.com/oauth/token",
        auth_client_id="client-123",
        auth_client_secret="secret-456",
        auth_redirect_uri="http://localhost/callback",
    )
    user_info_request = httpx.Request(
        "GET", "https://open.feishu.cn/open-apis/authen/v1/user_info"
    )
    user_info_response = httpx.Response(
        200,
        json={
            "code": 0,
            "data": {"open_id": "ou-test-user", "name": "测试用户"},
        },
        request=user_info_request,
    )
    store = MemoryTokenStore()
    store.set(TokenData(access_token="token-123", refresh_token="refresh-456", expires_at=None))
    client = FakeAsyncClient(get_response=user_info_response)
    service = AuthService(config=config, token_store=store, http_client=client)

    token = await service.ensure_cached_identity()
    assert token is not None
    assert token.open_id == "ou-test-user"
    assert token.account_name == "测试用户"
    loaded = store.get()
    assert loaded is not None
    assert loaded.open_id == "ou-test-user"
    assert loaded.account_name == "测试用户"


def test_token_store_roundtrip() -> None:
    store = MemoryTokenStore()
    token = TokenData(access_token="a", refresh_token="r", expires_at=None)
    store.set(token)
    loaded = store.get()
    assert loaded == token


def test_token_store_empty_refresh_token() -> None:
    """TokenData 支持空 refresh_token。"""
    store = MemoryTokenStore()
    token = TokenData(access_token="a", refresh_token="", expires_at=None)
    store.set(token)
    loaded = store.get()
    assert loaded is not None
    assert loaded.refresh_token == ""
