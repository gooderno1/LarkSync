from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from loguru import logger

from src.core.paths import data_dir
from src.services.account_service import AccountService
from src.services.device_flow_service import open_base_url


class TenantMetadataService:
    """使用应用身份只读补全账号所属组织，不影响用户授权状态。"""

    TENANT_READ_SCOPE = "tenant:tenant:readonly"
    MISSING_PERMISSION_CODE = "99991672"
    TENANT_UNAVAILABLE_CODE = "1184001"

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
            error_code = str(payload.get("code") or response.status_code)
            missing_scopes = self._missing_scopes(payload)
            if error_code == self.MISSING_PERMISSION_CODE and self.TENANT_READ_SCOPE in missing_scopes:
                permission_url = self._permission_url(
                    str(payload.get("msg") or ""),
                    brand=account.brand,
                    app_id=profile.app_id,
                )
                return await self._record_failure(
                    account_id,
                    status="permission_required",
                    message="需要为当前应用开通组织信息只读权限",
                    error_code=error_code,
                    permission_url=permission_url,
                    missing_scopes=missing_scopes,
                )
            if error_code == self.TENANT_UNAVAILABLE_CODE:
                return await self._record_failure(
                    account_id,
                    status="unavailable",
                    message="当前应用类型暂时无法读取组织信息，可继续使用账号与同步功能",
                    error_code=error_code,
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
                "tenant_metadata_error_code": None,
                "tenant_permission_url": None,
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

    async def _record_failure(
        self,
        account_id: str,
        *,
        status: str,
        message: str,
        error_code: str | None = None,
        permission_url: str | None = None,
        missing_scopes: list[str] | None = None,
    ) -> dict[str, object]:
        await self._accounts.update_tenant_metadata(
            account_id,
            tenant_metadata_status=status,
            tenant_metadata_error_code=error_code,
            tenant_permission_url=permission_url,
        )
        result: dict[str, object] = {"status": status, "message": message}
        if error_code:
            result["error_code"] = error_code
        if missing_scopes:
            result["missing_scopes"] = missing_scopes
        if permission_url:
            result["permission_url"] = permission_url
        return result

    @staticmethod
    def _missing_scopes(payload: dict[str, Any]) -> list[str]:
        error = payload.get("error")
        violations = error.get("permission_violations") if isinstance(error, dict) else None
        if not isinstance(violations, list):
            return []
        scopes: list[str] = []
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            subject = str(violation.get("subject") or "").strip()
            if subject and subject not in scopes:
                scopes.append(subject)
        return scopes

    @classmethod
    def _permission_url(cls, message: str, *, brand: str, app_id: str) -> str | None:
        """只接受错误响应中属于当前应用的官方权限地址，前端按原样生成二维码。"""
        expected_host = "open.larksuite.com" if brand == "lark" else "open.feishu.cn"
        expected_path = f"/app/{app_id}/auth"
        for match in re.findall(r"https://[^\s\"<>]+", message):
            candidate = match.rstrip("),.;，。；")
            parsed = urlparse(candidate)
            query = parse_qs(parsed.query)
            if (
                parsed.scheme == "https"
                and parsed.hostname == expected_host
                and parsed.path == expected_path
                and cls.TENANT_READ_SCOPE in query.get("q", [])
                and "tenant" in query.get("token_type", [])
            ):
                return candidate
        return None

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
