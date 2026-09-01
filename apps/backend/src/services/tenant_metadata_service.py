from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from src.core.paths import data_dir
from src.services.account_service import AccountService
from src.services.device_flow_service import open_base_url


class TenantMetadataService:
    """使用应用身份只读补全账号所属组织，不影响用户授权状态。"""

    def __init__(
        self,
        *,
        accounts: AccountService | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._accounts = accounts or AccountService()
        self._http_client = http_client

    async def refresh_account(self, account_id: str) -> dict[str, object]:
        account, profile, secret = await self._accounts.get_account_credentials(account_id)
        client = self._http_client or httpx.AsyncClient(timeout=30.0)
        should_close = self._http_client is None
        try:
            base_url = open_base_url(account.brand)
            token_response = await client.post(
                f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": profile.app_id, "app_secret": secret},
            )
            token_payload = self._payload(token_response)
            tenant_token = str(token_payload.get("tenant_access_token") or "").strip()
            if token_payload.get("code") != 0 or not tenant_token:
                return await self._record_failure(
                    account_id,
                    status="failed",
                    message=str(token_payload.get("msg") or "无法获取组织访问凭据"),
                )
            response = await client.get(
                f"{base_url}/open-apis/tenant/v2/tenant/query",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            payload = self._payload(response)
            if response.status_code == 403 or payload.get("code") == 1184001:
                return await self._record_failure(
                    account_id,
                    status="permission_required",
                    message="当前应用无权读取组织信息",
                )
            if response.status_code >= 400 or payload.get("code") != 0:
                return await self._record_failure(
                    account_id,
                    status="failed",
                    message=str(payload.get("msg") or "组织信息读取失败"),
                )
            data = payload.get("data")
            tenant = data.get("tenant") if isinstance(data, dict) else None
            if not isinstance(tenant, dict):
                return await self._record_failure(
                    account_id,
                    status="unavailable",
                    message="组织信息响应缺少 tenant",
                )
            avatar = tenant.get("avatar") if isinstance(tenant.get("avatar"), dict) else {}
            avatar_url = (
                self._text(avatar, "avatar_72")
                or self._text(avatar, "avatar_240")
                or self._text(avatar, "avatar_origin")
            )
            metadata: dict[str, object] = {
                "tenant_key": self._text(tenant, "tenant_key"),
                "tenant_name": self._text(tenant, "name"),
                "tenant_display_id": self._text(tenant, "display_id"),
                "tenant_tag": tenant.get("tenant_tag") if isinstance(tenant.get("tenant_tag"), int) else None,
                "tenant_avatar_url": avatar_url,
                "tenant_metadata_status": "ready",
            }
            cache_path = await self._cache_avatar(client, account_id, avatar_url)
            if cache_path is not None:
                metadata["tenant_avatar_cache_path"] = cache_path
            await self._accounts.update_tenant_metadata(account_id, **metadata)
            return {"status": "ready", **metadata}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("组织信息补全失败: account_id={} error_type={}", account_id, type(exc).__name__)
            return await self._record_failure(account_id, status="failed", message=str(exc))
        finally:
            if should_close:
                await client.aclose()

    async def _record_failure(self, account_id: str, *, status: str, message: str) -> dict[str, object]:
        await self._accounts.update_tenant_metadata(
            account_id,
            tenant_metadata_status=status,
        )
        return {"status": status, "message": message}

    @staticmethod
    async def _cache_avatar(
        client: httpx.AsyncClient,
        account_id: str,
        avatar_url: str | None,
    ) -> str | None:
        if not avatar_url or not avatar_url.lower().startswith("https://"):
            return None
        try:
            response = await client.get(avatar_url)
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(content_type)
            if response.status_code >= 400 or suffix is None or not response.content or len(response.content) > 2 * 1024 * 1024:
                return None
            cache_dir = data_dir() / "accounts" / account_id / "tenant"
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / f"avatar{suffix}"
            target.write_bytes(response.content)
            for stale in cache_dir.glob("avatar.*"):
                if stale != target and stale.is_file():
                    stale.unlink(missing_ok=True)
            return str(target)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("组织头像缓存失败: account_id={} error_type={}", account_id, type(exc).__name__)
            return None

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {"code": response.status_code, "msg": "响应不是 JSON"}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _text(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return str(value).strip() or None if value is not None else None


__all__ = ["TenantMetadataService"]
