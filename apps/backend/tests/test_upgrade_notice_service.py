from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.security import MemorySecretStore, MemoryTokenStore, TokenData
from src.db.base import Base
from src.services.account_service import AccountService
from src.services.upgrade_notice_service import UpgradeNoticeService


@pytest.mark.asyncio
async def test_upgrade_notice_targets_legacy_accounts_once() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    account_service = AccountService(
        session_maker=maker,
        secret_store=MemorySecretStore(),
        token_store_factory=lambda _account_id: MemoryTokenStore(),
        device_id="device-test",
    )
    profile = await account_service.create_app_profile(
        app_id="cli_test", app_secret="secret", brand="feishu", source="legacy"
    )
    legacy = await account_service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_legacy",
        account_name="旧账号",
        granted_scopes=[],
        token=TokenData("a", "r", None, auth_protocol="legacy_v1"),
        auth_protocol="legacy_v1",
    )
    await account_service.upsert_account(
        app_profile_id=profile.id,
        open_id="ou_device",
        account_name="新账号",
        granted_scopes=[],
        token=TokenData("a2", "r2", None, auth_protocol="device_v2"),
        auth_protocol="device_v2",
    )
    service = UpgradeNoticeService(session_maker=maker, account_service=account_service)

    assert await service.notify_for_version("v0.9.1") == 1
    assert await service.notify_for_version("v0.9.1") == 0
    notifications = await account_service.list_notifications(account_id=legacy.id)
    assert len(notifications) == 1
    assert notifications[0].action_target == f"account:reauthorize:{legacy.id}"
    await engine.dispose()
