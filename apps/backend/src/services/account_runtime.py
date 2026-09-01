from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from sqlalchemy import select

from src.core.config import AppConfig, ConfigManager
from src.core.security import SecretStore, get_secret_store
from src.db.models import Account, AppProfile
from src.db.session import get_session_maker
from src.services.device_flow_service import open_base_url
from src.core.account_context import current_account_id


@dataclass(frozen=True)
class AccountRuntime:
    account_id: str
    brand: str
    app_id: str
    app_secret: str

    def app_config(self) -> AppConfig:
        base = ConfigManager.get().config
        open_base = open_base_url(self.brand)
        return base.model_copy(
            update={
                "auth_client_id": self.app_id,
                "auth_client_secret": self.app_secret,
                "auth_token_url": f"{open_base}/open-apis/authen/v2/oauth/token",
            }
        )


class AccountRuntimeRegistry:
    """只缓存非敏感索引与进程内密钥；持久化密钥仍由系统安全存储负责。"""

    def __init__(self, secret_store: SecretStore | None = None) -> None:
        self._secret_store = secret_store or get_secret_store()
        self._items: dict[str, AccountRuntime] = {}
        self._lock = RLock()

    async def reload(self) -> None:
        session_maker = get_session_maker()
        async with session_maker() as session:
            rows = (
                await session.execute(
                    select(Account, AppProfile)
                    .join(AppProfile, Account.app_profile_id == AppProfile.id)
                    .where(
                        Account.removed_at.is_(None),
                        AppProfile.enabled.is_(True),
                    )
                )
            ).all()
        items: dict[str, AccountRuntime] = {}
        for account, profile in rows:
            secret = self._secret_store.get(profile.secret_ref)
            if not secret:
                continue
            items[account.id] = AccountRuntime(
                account_id=account.id,
                brand=account.brand,
                app_id=profile.app_id,
                app_secret=secret,
            )
        with self._lock:
            self._items = items

    def get(self, account_id: str | None) -> AccountRuntime | None:
        if not account_id:
            return None
        with self._lock:
            return self._items.get(account_id)


account_runtime_registry = AccountRuntimeRegistry()


def current_open_base_url() -> str:
    runtime = account_runtime_registry.get(current_account_id())
    return open_base_url(runtime.brand if runtime else "feishu")


__all__ = [
    "AccountRuntime",
    "AccountRuntimeRegistry",
    "account_runtime_registry",
    "current_open_base_url",
]
