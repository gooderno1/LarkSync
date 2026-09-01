from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import NotificationRecord, SyncMeta
from src.db.session import get_session_maker
from src.services.account_service import AccountService


class UpgradeNoticeService:
    """在新版本首次启动时向仍使用 V1 的账号发送一次升级授权建议。"""

    _META_KEY = "last_started_version"

    def __init__(
        self,
        *,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        account_service: AccountService | None = None,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._accounts = account_service or AccountService(session_maker=self._session_maker)

    async def notify_for_version(self, current_version: str) -> int:
        clean_version = current_version.strip()
        if not clean_version:
            return 0
        async with self._session_maker() as session:
            marker = await session.get(SyncMeta, self._META_KEY)
            if marker is not None and marker.value == clean_version:
                return 0

        created = 0
        for account in await self._accounts.list_accounts():
            if account.auth_protocol != "legacy_v1":
                continue
            source_id = f"auth-upgrade:{clean_version}:{account.id}"
            async with self._session_maker() as session:
                exists = (
                    await session.execute(
                        select(NotificationRecord.id).where(
                            NotificationRecord.account_id == account.id,
                            NotificationRecord.source_kind == "version_upgrade",
                            NotificationRecord.source_id == source_id,
                        )
                    )
                ).scalar_one_or_none()
            if exists:
                continue
            await self._accounts.create_notification(
                account_id=account.id,
                category="message",
                severity="info",
                title=f"LarkSync {clean_version} 已完成升级",
                body=(
                    "当前账号仍可通过 OAuth V1 兼容模式继续同步。建议重新授权一次，"
                    "升级为 Device Flow V2，以获得完整授权状态和后续兼容性保障。"
                ),
                source_kind="version_upgrade",
                source_id=source_id,
                action_target=f"account:reauthorize:{account.id}",
            )
            created += 1

        async with self._session_maker() as session:
            marker = await session.get(SyncMeta, self._META_KEY)
            now = time.time()
            if marker is None:
                session.add(SyncMeta(key=self._META_KEY, value=clean_version, updated_at=now))
            else:
                marker.value = clean_version
                marker.updated_at = now
            await session.commit()
        return created


__all__ = ["UpgradeNoticeService"]
