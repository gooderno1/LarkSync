from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.security import (
    CredentialStorageError,
    MemorySecretStore,
    MemoryTokenStore,
    TokenData,
)
from src.db.base import Base
from src.services.account_service import AccountService


@pytest.mark.asyncio
async def test_accounts_have_isolated_credentials_and_active_preference() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    secret_store = MemorySecretStore()
    token_stores: dict[str, MemoryTokenStore] = {}

    def token_store_factory(account_id: str) -> MemoryTokenStore:
        return token_stores.setdefault(account_id, MemoryTokenStore())

    service = AccountService(
        session_maker=maker,
        secret_store=secret_store,
        token_store_factory=token_store_factory,
        device_id="device-test",
    )
    profile = await service.create_app_profile(
        app_id="cli_test",
        app_secret="secret",
        brand="feishu",
        source="manual",
    )
    account_a = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_a",
        account_name="账号 A",
        granted_scopes=["drive:drive"],
        token=TokenData("access-a", "refresh-a", None, open_id="ou_a"),
        auth_protocol="device_v2",
    )
    account_b = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_b",
        account_name="账号 B",
        granted_scopes=["drive:drive"],
        token=TokenData("access-b", "refresh-b", None, open_id="ou_b"),
        auth_protocol="device_v2",
    )

    assert account_a.id != account_b.id
    assert account_a.account_alias == "飞书组织 1"
    assert account_b.account_alias == "飞书组织 2"
    assert token_stores[account_a.id].get().access_token == "access-a"
    assert token_stores[account_b.id].get().access_token == "access-b"
    await service.set_active_account(account_b.id)
    assert await service.get_active_account_id() == account_b.id

    await service.disconnect(account_a.id)
    assert token_stores[account_a.id].get() is None
    assert token_stores[account_b.id].get() is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_reauthorize_account_preserves_identity_and_switches_protocol() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    stores: dict[str, MemoryTokenStore] = {}
    service = AccountService(
        session_maker=maker,
        secret_store=MemorySecretStore(),
        token_store_factory=lambda account_id: stores.setdefault(account_id, MemoryTokenStore()),
        device_id="device-test",
    )
    profile = await service.create_app_profile(
        app_id="cli_test", app_secret="secret", brand="feishu", source="legacy"
    )
    account = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_a",
        account_name="账号 A",
        granted_scopes=[],
        token=TokenData("access-v1", "refresh-v1", None, open_id="ou_a", auth_protocol="legacy_v1"),
        auth_protocol="legacy_v1",
    )

    updated = await service.reauthorize_account(
        account_id=account.id,
        app_profile_id=profile.id,
        open_id="ou_a",
        account_name="账号 A 新名称",
        granted_scopes=["drive:drive"],
        token=TokenData("access-v2", "refresh-v2", None, open_id="ou_a", auth_protocol="device_v2"),
        tenant_key="tenant-alpha",
    )

    assert updated.id == account.id
    assert updated.auth_protocol == "device_v2"
    assert updated.tenant_key == "tenant-alpha"
    assert updated.account_alias == "飞书组织 1"
    assert stores[account.id].get().access_token == "access-v2"
    with pytest.raises(ValueError, match="扫码账号与目标账号不一致"):
        await service.reauthorize_account(
            account_id=account.id,
            app_profile_id=profile.id,
            open_id="ou_other",
            account_name="其他账号",
            granted_scopes=[],
            token=TokenData("other", "other-refresh", None, open_id="ou_other", auth_protocol="device_v2"),
        )
    assert stores[account.id].get().access_token == "access-v2"
    await engine.dispose()


@pytest.mark.asyncio
async def test_official_organization_name_avoids_preset_and_empty_alias_restores_safe_name() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    service = AccountService(
        session_maker=maker,
        secret_store=MemorySecretStore(),
        token_store_factory=lambda _account_id: MemoryTokenStore(),
        device_id="device-test",
    )
    profile = await service.create_app_profile(
        app_id="cli_test", app_secret="secret", brand="feishu", source="manual"
    )
    official = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_official",
        account_name="账号 A",
        granted_scopes=[],
        token=TokenData("access", "refresh", None, open_id="ou_official"),
        tenant_name="青鸟科技",
        tenant_key="tenant-alpha",
    )
    assert official.tenant_name == "青鸟科技"
    assert official.tenant_key == "tenant-alpha"
    assert official.account_alias is None

    preset = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_preset",
        account_name="账号 B",
        granted_scopes=[],
        token=TokenData("access-2", "refresh-2", None, open_id="ou_preset"),
    )
    assert preset.account_alias == "飞书组织 1"
    renamed = await service.set_account_alias(preset.id, "采购团队")
    assert renamed.account_alias == "采购团队"
    restored = await service.set_account_alias(preset.id, None)
    assert restored.account_alias == "飞书组织 1"
    await engine.dispose()


@pytest.mark.asyncio
async def test_reauthorize_restores_previous_token_when_database_commit_fails() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    stores: dict[str, MemoryTokenStore] = {}
    secret_store = MemorySecretStore()

    def token_store_factory(account_id: str) -> MemoryTokenStore:
        return stores.setdefault(account_id, MemoryTokenStore())

    service = AccountService(
        session_maker=maker,
        secret_store=secret_store,
        token_store_factory=token_store_factory,
        device_id="device-test",
    )
    profile = await service.create_app_profile(
        app_id="cli_test", app_secret="secret", brand="feishu", source="legacy"
    )
    account = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_a",
        account_name="账号 A",
        granted_scopes=[],
        token=TokenData(
            "access-v1",
            "refresh-v1",
            None,
            open_id="ou_a",
            auth_protocol="legacy_v1",
        ),
        auth_protocol="legacy_v1",
    )

    @asynccontextmanager
    async def failing_session_maker():
        async with maker() as session:
            async def fail_commit() -> None:
                raise RuntimeError("database commit failed")

            session.commit = fail_commit  # type: ignore[method-assign]
            yield session

    failing_service = AccountService(
        session_maker=failing_session_maker,  # type: ignore[arg-type]
        secret_store=secret_store,
        token_store_factory=token_store_factory,
        device_id="device-test",
    )

    with pytest.raises(CredentialStorageError, match="新凭据已安全回退"):
        await failing_service.reauthorize_account(
            account_id=account.id,
            app_profile_id=profile.id,
            open_id="ou_a",
            account_name="账号 A",
            granted_scopes=["drive:drive"],
            token=TokenData(
                "access-v2",
                "refresh-v2",
                None,
                open_id="ou_a",
                auth_protocol="device_v2",
            ),
        )

    restored = stores[account.id].get()
    assert restored is not None
    assert restored.access_token == "access-v1"
    assert restored.auth_protocol == "legacy_v1"
    unchanged = await service.get_account(account.id)
    assert unchanged is not None
    assert unchanged.auth_protocol == "legacy_v1"
    await engine.dispose()


def test_legacy_migration_never_overwrites_scoped_v2_token() -> None:
    selected = AccountService._select_legacy_migration_token(
        account_protocol="device_v2",
        scoped_token=TokenData(
            "access-v2", "refresh-v2", None, auth_protocol="device_v2"
        ),
        legacy_token=TokenData(
            "access-v1", "refresh-v1", None, auth_protocol="legacy_v1"
        ),
    )

    assert selected is not None
    assert selected.access_token == "access-v2"
    assert selected.auth_protocol == "device_v2"


@pytest.mark.asyncio
async def test_account_summary_keeps_unread_counts_separate() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    service = AccountService(
        session_maker=maker,
        secret_store=MemorySecretStore(),
        token_store_factory=lambda _account_id: MemoryTokenStore(),
        device_id="device-test",
    )
    profile = await service.create_app_profile(
        app_id="cli_test", app_secret="secret", brand="feishu", source="manual"
    )
    account = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_a",
        account_name="账号 A",
        granted_scopes=[],
        token=TokenData("access", "refresh", None, open_id="ou_a"),
        auth_protocol="device_v2",
    )
    await service.create_notification(
        account_id=account.id,
        category="sync_error",
        severity="error",
        title="同步失败",
        body="任务 A 失败",
    )
    await service.create_notification(
        account_id=account.id,
        category="message",
        severity="info",
        title="已完成迁移",
        body="旧数据已经迁移",
    )
    summary = await service.list_account_summaries()
    assert summary[0].unread_total == 2
    assert summary[0].unread_errors == 1
    assert summary[0].unread_messages == 1
    await engine.dispose()
