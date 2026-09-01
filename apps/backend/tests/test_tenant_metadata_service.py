from __future__ import annotations

import httpx
import pytest

from src.services.tenant_metadata_service import TenantMetadataService


class _Accounts:
    def __init__(self) -> None:
        self.saved: tuple[str, dict[str, object]] | None = None

    async def get_account_credentials(self, account_id: str):
        account = type("Account", (), {"id": account_id, "brand": "feishu"})()
        profile = type("Profile", (), {"app_id": "cli_test"})()
        return account, profile, "secret"

    async def update_tenant_metadata(self, account_id: str, **metadata):
        self.saved = (account_id, metadata)
        return metadata


@pytest.mark.asyncio
async def test_refresh_tenant_metadata_persists_official_identity(tmp_path, monkeypatch) -> None:
    accounts = _Accounts()
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v3/tenant_access_token/internal"):
            return httpx.Response(200, request=request, json={"code": 0, "tenant_access_token": "tenant-token"})
        if request.url.host == "example.test":
            return httpx.Response(200, request=request, headers={"content-type": "image/png"}, content=b"png-bytes")
        assert request.headers["Authorization"] == "Bearer tenant-token"
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {
                    "tenant": {
                        "name": "示例组织",
                        "display_id": "F123",
                        "tenant_key": "tenant-key",
                        "tenant_tag": 0,
                        "avatar": {"avatar_72": "https://example.test/logo.png"},
                    }
                },
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = TenantMetadataService(accounts=accounts, http_client=client)  # type: ignore[arg-type]
    result = await service.refresh_account("account-a")

    assert result["status"] == "ready"
    assert accounts.saved == (
        "account-a",
        {
            "tenant_key": "tenant-key",
            "tenant_name": "示例组织",
            "tenant_display_id": "F123",
            "tenant_tag": 0,
            "tenant_avatar_url": "https://example.test/logo.png",
            "tenant_avatar_cache_path": str(tmp_path / "accounts" / "account-a" / "tenant" / "avatar.png"),
            "tenant_metadata_status": "ready",
        },
    )
    assert (tmp_path / "accounts" / "account-a" / "tenant" / "avatar.png").read_bytes() == b"png-bytes"
    await client.aclose()


@pytest.mark.asyncio
async def test_refresh_tenant_metadata_degrades_without_permission() -> None:
    accounts = _Accounts()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v3/tenant_access_token/internal"):
            return httpx.Response(200, request=request, json={"code": 0, "tenant_access_token": "tenant-token"})
        return httpx.Response(403, request=request, json={"code": 1184001, "msg": "forbidden"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = TenantMetadataService(accounts=accounts, http_client=client)  # type: ignore[arg-type]
    result = await service.refresh_account("account-a")

    assert result == {"status": "permission_required", "message": "当前应用无权读取组织信息"}
    assert accounts.saved == (
        "account-a",
        {
            "tenant_metadata_status": "permission_required",
        },
    )
    await client.aclose()
