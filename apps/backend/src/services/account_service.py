from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Callable

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.device import current_device_id
from src.core.config import ConfigManager
from src.core.security import (
    CredentialStorageError,
    SecretStore,
    TokenData,
    TokenStore,
    get_secret_store,
    get_token_store,
)
from src.db.models import (
    Account,
    AppProfile,
    NotificationRecord,
    UiPreference,
    LEGACY_ACCOUNT_ID,
)
from src.db.session import get_session_maker
from src.services.device_flow_service import normalize_brand


@dataclass(frozen=True)
class AppProfileItem:
    id: str
    brand: str
    app_id: str
    display_name: str | None
    source: str
    enabled: bool
    has_secret: bool


@dataclass(frozen=True)
class AccountItem:
    id: str
    app_profile_id: str
    brand: str
    open_id: str
    account_name: str | None
    avatar_url: str | None
    tenant_name: str | None
    tenant_key: str | None
    tenant_display_id: str | None
    tenant_tag: int | None
    tenant_avatar_url: str | None
    tenant_avatar_cache_path: str | None
    tenant_metadata_status: str | None
    tenant_metadata_error_code: str | None
    tenant_permission_url: str | None
    tenant_metadata_updated_at: float | None
    account_alias: str | None
    state: str
    granted_scopes: list[str]
    paused: bool
    auth_protocol: str
    access_expires_at: float | None
    refresh_expires_at: float | None
    last_auth_error: str | None
    created_at: float
    updated_at: float


@dataclass(frozen=True)
class AccountSummary(AccountItem):
    unread_total: int = 0
    unread_errors: int = 0
    unread_messages: int = 0
    is_active: bool = False


@dataclass(frozen=True)
class NotificationItem:
    id: str
    account_id: str
    category: str
    severity: str
    title: str
    body: str
    source_kind: str | None
    source_id: str | None
    task_id: str | None
    action_target: str | None
    created_at: float
    read_at: float | None


class AccountService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        secret_store: SecretStore | None = None,
        token_store_factory: Callable[[str], TokenStore] | None = None,
        device_id: str | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._secret_store = secret_store or get_secret_store()
        self._token_store_factory = token_store_factory or get_token_store
        self._device_id = device_id or current_device_id()

    async def create_app_profile(
        self,
        *,
        app_id: str,
        app_secret: str,
        brand: str,
        source: str,
        display_name: str | None = None,
    ) -> AppProfileItem:
        clean_app_id = app_id.strip()
        clean_secret = app_secret.strip()
        if not clean_app_id or not clean_secret:
            raise ValueError("App ID 和 App Secret 不能为空")
        clean_brand = normalize_brand(brand)
        async with self._session_maker() as session:
            existing = (
                await session.execute(
                    select(AppProfile).where(
                        AppProfile.brand == clean_brand,
                        AppProfile.app_id == clean_app_id,
                    )
                )
            ).scalar_one_or_none()
            now = time.time()
            if existing is None:
                profile_id = str(uuid.uuid4())
                existing = AppProfile(
                    id=profile_id,
                    brand=clean_brand,
                    app_id=clean_app_id,
                    display_name=(display_name or "").strip() or None,
                    source=source.strip() or "manual",
                    secret_ref=f"app-profile:{profile_id}",
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(existing)
            else:
                existing.enabled = True
                existing.updated_at = now
                if display_name is not None:
                    existing.display_name = display_name.strip() or None
            self._secret_store.set(existing.secret_ref, clean_secret)
            await session.commit()
            return self._profile_item(existing)

    async def migrate_legacy_install(self) -> bool:
        """把 v0.8 的全局配置与凭据自动复制到 v0.9 账户命名空间。

        数据库升级前备份已由 ``init_db`` 完成。仅在安全存储写入成功后，才会
        从 config.json 清除明文 App Secret，因此升级不需要用户手动搬迁数据。
        """
        config_manager = ConfigManager.get()
        config = config_manager.config
        async with self._session_maker() as session:
            account = await session.get(Account, LEGACY_ACCOUNT_ID)
            profile = await session.get(AppProfile, "legacy-default-app")
            if account is None or profile is None:
                return False
            app_id = config.auth_client_id.strip()
            app_secret = config.auth_client_secret.strip()
            if app_id:
                profile.app_id = app_id
            if app_secret:
                self._secret_store.set(profile.secret_ref, app_secret)
            scoped_store = self._token_store_factory(LEGACY_ACCOUNT_ID)
            scoped_token = scoped_store.get()
            legacy_token = self._token_store_factory("").get()
            # V2 重新授权后，账号命名空间中的凭据就是新的事实来源。后续启动
            # 不能再用仍留在全局命名空间中的 v0.8 凭据把它覆盖回 V1。
            migrated_token = self._select_legacy_migration_token(
                account_protocol=account.auth_protocol,
                scoped_token=scoped_token,
                legacy_token=legacy_token,
            )
            if migrated_token is not None:
                protocol = migrated_token.auth_protocol
                scoped_store.set(migrated_token)
                if migrated_token.open_id:
                    account.open_id = migrated_token.open_id
                account.account_name = migrated_token.account_name or account.account_name
                account.state = "connected"
                account.auth_protocol = protocol
                account.granted_scopes = self._serialize_scopes(
                    (migrated_token.scope or "").split()
                )
            elif app_id and app_secret:
                account.state = "auth_required"
            profile.updated_at = time.time()
            account.updated_at = time.time()
            preference = await session.get(UiPreference, self._device_id)
            if preference is None:
                session.add(
                    UiPreference(
                        device_id=self._device_id,
                        active_account_id=LEGACY_ACCOUNT_ID,
                        updated_at=time.time(),
                    )
                )
            await session.commit()
        if app_secret:
            payload = config.model_dump(mode="json")
            payload["auth_client_secret"] = ""
            config_manager.save_config(payload)
        return True

    @staticmethod
    def _select_legacy_migration_token(
        *,
        account_protocol: str,
        scoped_token: TokenData | None,
        legacy_token: TokenData | None,
    ) -> TokenData | None:
        token = scoped_token or legacy_token
        if token is None:
            return None
        protocol = (
            "device_v2"
            if account_protocol == "device_v2" and scoped_token is not None
            else "legacy_v1"
        )
        return TokenData(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at,
            open_id=token.open_id,
            account_name=token.account_name,
            scope=token.scope,
            refresh_expires_at=token.refresh_expires_at,
            auth_protocol=protocol,
        )

    async def list_app_profiles(self) -> list[AppProfileItem]:
        async with self._session_maker() as session:
            records = (
                await session.execute(
                    select(AppProfile)
                    .where(AppProfile.enabled.is_(True))
                    .order_by(AppProfile.created_at.asc())
                )
            ).scalars().all()
        return [self._profile_item(record) for record in records]

    async def get_app_profile_credentials(
        self, profile_id: str
    ) -> tuple[AppProfileItem, str]:
        async with self._session_maker() as session:
            record = await session.get(AppProfile, profile_id)
            if record is None or not record.enabled:
                raise ValueError("应用配置不存在或已停用")
            secret = self._secret_store.get(record.secret_ref)
            if not secret:
                raise ValueError("应用密钥不存在，请重新配置")
            return self._profile_item(record), secret

    async def get_account_credentials(
        self, account_id: str
    ) -> tuple[AccountItem, AppProfileItem, str]:
        account = await self.get_account(account_id)
        if account is None:
            raise ValueError("账号不存在")
        profile, secret = await self.get_app_profile_credentials(
            account.app_profile_id
        )
        return account, profile, secret

    async def upsert_account(
        self,
        *,
        app_profile_id: str,
        open_id: str,
        account_name: str | None,
        granted_scopes: list[str],
        token: TokenData,
        auth_protocol: str = "device_v2",
        avatar_url: str | None = None,
        tenant_name: str | None = None,
    ) -> AccountItem:
        profile, _secret = await self.get_app_profile_credentials(app_profile_id)
        clean_open_id = open_id.strip()
        if not clean_open_id:
            raise ValueError("授权响应缺少 open_id")
        async with self._session_maker() as session:
            record = (
                await session.execute(
                    select(Account).where(
                        Account.brand == profile.brand,
                        Account.app_profile_id == app_profile_id,
                        Account.open_id == clean_open_id,
                    )
                )
            ).scalar_one_or_none()
            now = time.time()
            if record is None:
                record = Account(
                    id=str(uuid.uuid4()),
                    app_profile_id=app_profile_id,
                    brand=profile.brand,
                    open_id=clean_open_id,
                    account_name=(account_name or "").strip() or None,
                    avatar_url=avatar_url,
                    tenant_name=tenant_name,
                    state="connected",
                    granted_scopes=self._serialize_scopes(granted_scopes),
                    paused=False,
                    last_auth_error=None,
                    auth_protocol=auth_protocol,
                    created_at=now,
                    updated_at=now,
                    removed_at=None,
                )
                session.add(record)
            else:
                record.account_name = (account_name or "").strip() or record.account_name
                record.avatar_url = avatar_url or record.avatar_url
                record.tenant_name = tenant_name or record.tenant_name
                record.state = "connected"
                record.granted_scopes = self._serialize_scopes(granted_scopes)
                record.last_auth_error = None
                record.auth_protocol = auth_protocol
                record.removed_at = None
                record.updated_at = now
            await session.flush()
            persisted = TokenData(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at,
                open_id=clean_open_id,
                account_name=record.account_name,
                scope=token.scope,
                refresh_expires_at=token.refresh_expires_at,
                auth_protocol=auth_protocol,
            )
            await self._persist_token_and_commit(
                session, self._token_store_factory(record.id), persisted
            )
            account = self._account_item(record)
        if await self.get_active_account_id() is None:
            await self.set_active_account(account.id)
        return account

    async def reauthorize_account(
        self,
        *,
        account_id: str,
        app_profile_id: str,
        open_id: str,
        account_name: str | None,
        granted_scopes: list[str],
        token: TokenData,
        avatar_url: str | None = None,
        tenant_name: str | None = None,
    ) -> AccountItem:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            if record.app_profile_id != app_profile_id:
                raise ValueError("重新授权必须使用原应用配置")
            if record.open_id != open_id.strip():
                raise ValueError("扫码账号与目标账号不一致，请使用原账号重新扫码")
            now = time.time()
            record.account_name = (account_name or "").strip() or record.account_name
            record.avatar_url = avatar_url or record.avatar_url
            record.tenant_name = tenant_name or record.tenant_name
            record.state = "connected"
            record.auth_protocol = "device_v2"
            record.granted_scopes = self._serialize_scopes(granted_scopes)
            record.last_auth_error = None
            record.updated_at = now
            persisted = TokenData(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at,
                open_id=record.open_id,
                account_name=record.account_name,
                scope=token.scope,
                refresh_expires_at=token.refresh_expires_at,
                auth_protocol="device_v2",
            )
            await self._persist_token_and_commit(
                session, self._token_store_factory(record.id), persisted
            )
            return self._account_item(record)

    @staticmethod
    async def _persist_token_and_commit(
        session: AsyncSession, token_store: TokenStore, token: TokenData
    ) -> None:
        previous = token_store.reload()
        token_store.set(token)
        try:
            await session.commit()
        except Exception as commit_exc:
            try:
                if previous is None:
                    token_store.clear()
                else:
                    token_store.set(previous)
            except Exception as rollback_exc:
                logger.error(
                    "账号数据库提交失败后旧凭据恢复失败: error_type={}",
                    type(rollback_exc).__name__,
                )
                raise CredentialStorageError(
                    "账号状态保存失败，旧凭据恢复也失败"
                ) from rollback_exc
            raise CredentialStorageError(
                "账号状态保存失败，新凭据已安全回退"
            ) from commit_exc

    async def list_accounts(self, *, include_removed: bool = False) -> list[AccountItem]:
        stmt = select(Account).order_by(Account.created_at.asc())
        if not include_removed:
            stmt = stmt.where(Account.removed_at.is_(None))
        async with self._session_maker() as session:
            records = (await session.execute(stmt)).scalars().all()
        return [self._account_item(record) for record in records]

    async def get_account(self, account_id: str) -> AccountItem | None:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                return None
            return self._account_item(record)

    async def set_active_account(self, account_id: str | None) -> None:
        if account_id:
            account = await self.get_account(account_id)
            if account is None:
                raise ValueError("账号不存在")
        async with self._session_maker() as session:
            record = await session.get(UiPreference, self._device_id)
            now = time.time()
            if record is None:
                session.add(
                    UiPreference(
                        device_id=self._device_id,
                        active_account_id=account_id,
                        updated_at=now,
                    )
                )
            else:
                record.active_account_id = account_id
                record.updated_at = now
            await session.commit()

    async def get_active_account_id(self) -> str | None:
        async with self._session_maker() as session:
            preference = await session.get(UiPreference, self._device_id)
            if preference and preference.active_account_id:
                record = await session.get(Account, preference.active_account_id)
                if record and record.removed_at is None:
                    return record.id
            first = (
                await session.execute(
                    select(Account.id)
                    .where(Account.removed_at.is_(None))
                    .order_by(Account.created_at.asc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return first

    async def disconnect(self, account_id: str) -> None:
        self._token_store_factory(account_id).clear()
        await self._set_account_state(account_id, state="auth_required")

    async def record_auth_result(
        self, account_id: str, *, state: str, error: str | None = None
    ) -> None:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            record.state = state
            record.last_auth_error = error
            record.updated_at = time.time()
            await session.commit()

    async def set_paused(self, account_id: str, paused: bool) -> None:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            record.paused = bool(paused)
            record.updated_at = time.time()
            await session.commit()

    async def update_tenant_metadata(
        self,
        account_id: str,
        *,
        tenant_key: str | None = None,
        tenant_name: str | None = None,
        tenant_display_id: str | None = None,
        tenant_tag: int | None = None,
        tenant_avatar_url: str | None = None,
        tenant_avatar_cache_path: str | None = None,
        tenant_metadata_status: str,
        tenant_metadata_error_code: str | None = None,
        tenant_permission_url: str | None = None,
    ) -> AccountItem:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            if tenant_key is not None:
                record.tenant_key = tenant_key.strip() or record.tenant_key
            if tenant_name is not None:
                record.tenant_name = tenant_name.strip() or record.tenant_name
            if tenant_display_id is not None:
                record.tenant_display_id = tenant_display_id.strip() or record.tenant_display_id
            if tenant_tag is not None:
                record.tenant_tag = int(tenant_tag)
            if tenant_avatar_url is not None:
                record.tenant_avatar_url = tenant_avatar_url.strip() or record.tenant_avatar_url
            if tenant_avatar_cache_path is not None:
                record.tenant_avatar_cache_path = tenant_avatar_cache_path.strip() or record.tenant_avatar_cache_path
            record.tenant_metadata_status = tenant_metadata_status
            record.tenant_metadata_error_code = tenant_metadata_error_code
            record.tenant_permission_url = tenant_permission_url
            record.tenant_metadata_updated_at = time.time()
            record.updated_at = time.time()
            await session.commit()
            return self._account_item(record)

    async def set_account_alias(self, account_id: str, alias: str | None) -> AccountItem:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            record.account_alias = (alias or "").strip() or None
            record.updated_at = time.time()
            await session.commit()
            return self._account_item(record)

    async def remove(self, account_id: str) -> None:
        self._token_store_factory(account_id).clear()
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None:
                raise ValueError("账号不存在")
            now = time.time()
            record.state = "removed"
            record.removed_at = now
            record.updated_at = now
            await session.commit()
        if await self.get_active_account_id() == account_id:
            await self.set_active_account(None)

    async def _set_account_state(self, account_id: str, *, state: str) -> None:
        async with self._session_maker() as session:
            record = await session.get(Account, account_id)
            if record is None or record.removed_at is not None:
                raise ValueError("账号不存在")
            record.state = state
            record.updated_at = time.time()
            await session.commit()

    async def create_notification(
        self,
        *,
        account_id: str,
        category: str,
        severity: str,
        title: str,
        body: str,
        source_kind: str | None = None,
        source_id: str | None = None,
        task_id: str | None = None,
        action_target: str | None = None,
    ) -> NotificationItem:
        record = NotificationRecord(
            id=str(uuid.uuid4()),
            account_id=account_id,
            category=category,
            severity=severity,
            title=title.strip(),
            body=body.strip(),
            source_kind=source_kind,
            source_id=source_id,
            task_id=task_id,
            action_target=action_target,
            created_at=time.time(),
            read_at=None,
        )
        async with self._session_maker() as session:
            session.add(record)
            await session.commit()
        return self._notification_item(record)

    async def list_notifications(
        self,
        *,
        account_id: str | None = None,
        unread_only: bool = False,
        limit: int = 100,
    ) -> list[NotificationItem]:
        stmt = select(NotificationRecord)
        if account_id:
            stmt = stmt.where(NotificationRecord.account_id == account_id)
        if unread_only:
            stmt = stmt.where(NotificationRecord.read_at.is_(None))
        stmt = stmt.order_by(NotificationRecord.created_at.desc()).limit(max(1, min(limit, 500)))
        async with self._session_maker() as session:
            records = (await session.execute(stmt)).scalars().all()
        return [self._notification_item(record) for record in records]

    async def mark_notification_read(self, notification_id: str, *, read: bool = True) -> None:
        async with self._session_maker() as session:
            record = await session.get(NotificationRecord, notification_id)
            if record is None:
                raise ValueError("通知不存在")
            record.read_at = time.time() if read else None
            await session.commit()

    async def mark_all_notifications_read(self, account_id: str | None = None) -> int:
        items = await self.list_notifications(account_id=account_id, unread_only=True, limit=500)
        if not items:
            return 0
        ids = [item.id for item in items]
        async with self._session_maker() as session:
            records = (
                await session.execute(
                    select(NotificationRecord).where(NotificationRecord.id.in_(ids))
                )
            ).scalars().all()
            now = time.time()
            for record in records:
                record.read_at = now
            await session.commit()
        return len(records)

    async def list_account_summaries(self) -> list[AccountSummary]:
        accounts = await self.list_accounts()
        active_id = await self.get_active_account_id()
        async with self._session_maker() as session:
            rows = (
                await session.execute(
                    select(
                        NotificationRecord.account_id,
                        func.count(NotificationRecord.id),
                        func.sum(
                            case(
                                (NotificationRecord.category == "sync_error", 1),
                                else_=0,
                            )
                        ),
                    )
                    .where(NotificationRecord.read_at.is_(None))
                    .group_by(NotificationRecord.account_id)
                )
            ).all()
        counts = {
            str(row[0]): (int(row[1] or 0), int(row[2] or 0))
            for row in rows
        }
        summaries: list[AccountSummary] = []
        for account in accounts:
            unread_total, unread_errors = counts.get(account.id, (0, 0))
            summaries.append(
                AccountSummary(
                    **account.__dict__,
                    unread_total=unread_total,
                    unread_errors=unread_errors,
                    unread_messages=max(0, unread_total - unread_errors),
                    is_active=account.id == active_id,
                )
            )
        return summaries

    def _profile_item(self, record: AppProfile) -> AppProfileItem:
        return AppProfileItem(
            id=record.id,
            brand=record.brand,
            app_id=record.app_id,
            display_name=record.display_name,
            source=record.source,
            enabled=bool(record.enabled),
            has_secret=bool(self._secret_store.get(record.secret_ref)),
        )

    def _account_item(self, record: Account) -> AccountItem:
        token = self._token_store_factory(record.id).get()
        return AccountItem(
            id=record.id,
            app_profile_id=record.app_profile_id,
            brand=record.brand,
            open_id=record.open_id,
            account_name=record.account_name,
            avatar_url=record.avatar_url,
            tenant_name=record.tenant_name,
            tenant_key=record.tenant_key,
            tenant_display_id=record.tenant_display_id,
            tenant_tag=record.tenant_tag,
            tenant_avatar_url=record.tenant_avatar_url,
            tenant_avatar_cache_path=record.tenant_avatar_cache_path,
            tenant_metadata_status=record.tenant_metadata_status,
            tenant_metadata_error_code=record.tenant_metadata_error_code,
            tenant_permission_url=record.tenant_permission_url,
            tenant_metadata_updated_at=record.tenant_metadata_updated_at,
            account_alias=record.account_alias,
            state=record.state,
            granted_scopes=self._parse_scopes(record.granted_scopes),
            paused=bool(record.paused),
            auth_protocol=record.auth_protocol,
            access_expires_at=token.expires_at if token else None,
            refresh_expires_at=token.refresh_expires_at if token else None,
            last_auth_error=record.last_auth_error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _notification_item(record: NotificationRecord) -> NotificationItem:
        return NotificationItem(
            id=record.id,
            account_id=record.account_id,
            category=record.category,
            severity=record.severity,
            title=record.title,
            body=record.body,
            source_kind=record.source_kind,
            source_id=record.source_id,
            task_id=record.task_id,
            action_target=record.action_target,
            created_at=record.created_at,
            read_at=record.read_at,
        )

    @staticmethod
    def _serialize_scopes(scopes: list[str]) -> str:
        return json.dumps(sorted({scope.strip() for scope in scopes if scope.strip()}))

    @staticmethod
    def _parse_scopes(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return [scope for scope in value.split() if scope]
        if not isinstance(payload, list):
            return []
        return [str(scope) for scope in payload if str(scope).strip()]


__all__ = [
    "AccountItem",
    "AccountService",
    "AccountSummary",
    "AppProfileItem",
    "NotificationItem",
]
