from urllib.parse import parse_qs, urlparse

import pytest

from src.core.config import AppConfig
from src.core.security import MemoryTokenStore, TokenData
from src.services.auth_service import AuthError, AuthService


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
    assert params["response_type"] == ["code"]
    assert params["state"] == ["state-xyz"]
    assert params["scope"] == ["scope.read scope.write"]


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


def test_token_store_roundtrip() -> None:
    store = MemoryTokenStore()
    token = TokenData(access_token="a", refresh_token="r", expires_at=None)
    store.set(token)
    loaded = store.get()
    assert loaded == token
