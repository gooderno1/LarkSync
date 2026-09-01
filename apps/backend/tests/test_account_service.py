from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.security import MemorySecretStore, MemoryTokenStore, TokenData
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
    )
    account_b = await service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_b",
        account_name="账号 B",
        granted_scopes=["drive:drive"],
        token=TokenData("access-b", "refresh-b", None, open_id="ou_b"),
    )

    assert account_a.id != account_b.id
    assert token_stores[account_a.id].get().access_token == "access-a"
    assert token_stores[account_b.id].get().access_token == "access-b"
    await service.set_active_account(account_b.id)
    assert await service.get_active_account_id() == account_b.id

    await service.disconnect(account_a.id)
    assert token_stores[account_a.id].get() is None
    assert token_stores[account_b.id].get() is not None

    await engine.dispose()


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
