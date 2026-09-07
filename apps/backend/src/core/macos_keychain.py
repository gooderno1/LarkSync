"""macOS Keychain：后台不弹窗，显式恢复允许交互，更新保留条目身份。"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from threading import Lock, RLock
from typing import Any, Iterator

from keyring.errors import KeyringError


ACCESS_MESSAGE = "macOS 钥匙串访问已暂停。请点击“重试钥匙串访问”，按系统提示授权。账号和同步数据仍保留。"


class KeychainAccessError(KeyringError):
    """只包含安全的操作状态，不包含钥匙串数据。"""


def enabled() -> bool:
    return sys.platform == "darwin"


@lru_cache(maxsize=1)
def _frameworks() -> tuple[Any, Any]:
    import Foundation
    import Security

    return Security, Foundation


class MacOSKeychain:
    def __init__(self) -> None:
        self._blocked = False
        self._retrying = False
        self._operations = RLock()
        self._retry_lock = Lock()
        self._pending: set[tuple[str, str]] = set()
        self._current_item: tuple[str, str] | None = None
        self._interactive: ContextVar[bool] = ContextVar("keychain_interactive", default=False)

    def status(self) -> dict[str, object]:
        return {"supported": True, "blocked": self._blocked,
                "retrying": self._retrying, "message": ACCESS_MESSAGE if self._blocked else None}

    def ensure_available(self) -> None:
        # 不等待正在交互的线程，否则同步调用会阻塞 FastAPI 事件循环。
        if self._blocked or (self._retrying and not self._interactive.get()):
            raise KeychainAccessError(ACCESS_MESSAGE)

    @contextmanager
    def interactive_retry(self) -> Iterator[None]:
        if not self._retry_lock.acquire(blocking=False):
            raise KeychainAccessError("正在等待钥匙串授权，请完成当前系统提示。")
        self._retrying = True
        self._blocked = False
        token = self._interactive.set(True)
        try:
            yield
        except Exception:
            self._blocked = True
            raise
        finally:
            self._interactive.reset(token)
            self._retrying = False
            self._retry_lock.release()

    @contextmanager
    def _operation(self) -> Iterator[tuple[Any, Any]]:
        self.ensure_available()
        with self._operations:
            self.ensure_available()
            try:
                api, foundation = _frameworks()
                # 文件型登录钥匙串会忽略 SecItem 的 UI 参数（Chromium FB16959400）。
                # 进程内串行设置，调用完成或失败都恢复，绝不更改系统/其他进程策略。
                status, was_allowed = api.SecKeychainGetUserInteractionAllowed(None)
                self._check(status)
                self._check(api.SecKeychainSetUserInteractionAllowed(self._interactive.get()))
                try:
                    yield api, foundation
                finally:
                    self._check(api.SecKeychainSetUserInteractionAllowed(was_allowed))
            except KeychainAccessError:
                raise
            except Exception as exc:
                self._blocked = True
                raise KeychainAccessError(ACCESS_MESSAGE) from exc

    def _query(self, api: Any, service: str, account: str) -> dict[Any, Any]:
        self._current_item = (service, account)
        query = {api.kSecClass: api.kSecClassGenericPassword,
                 api.kSecAttrService: service, api.kSecAttrAccount: account}
        if not self._interactive.get():
            # 兼容 macOS 12 的文件钥匙串；不使用 UISkip，避免把未授权误当成不存在。
            query[api.kSecUseAuthenticationUI] = api.kSecUseAuthenticationUIFail
        return query

    def _check(self, status: int) -> None:
        if status != 0:
            self._blocked = True
            if self._current_item is not None:
                self._pending.add(self._current_item)
            raise KeychainAccessError(f"{ACCESS_MESSAGE}（系统状态 {status}）")

    def retry_pending(self) -> None:
        if not self._interactive.get():
            raise KeychainAccessError("钥匙串恢复需要用户主动操作。")
        for service, account in tuple(self._pending):
            self.get_password(service, account)
            self._pending.discard((service, account))

    def get_password(self, service: str, account: str) -> str | None:
        with self._operation() as (api, _foundation):
            query = self._query(api, service, account)
            query.update({api.kSecReturnData: True, api.kSecMatchLimit: api.kSecMatchLimitOne})
            status, value = api.SecItemCopyMatching(query, None)
            if status == api.errSecItemNotFound:
                return None
            self._check(status)
            return bytes(value).decode("utf-8")

    def set_password(self, service: str, account: str, value: str) -> None:
        with self._operation() as (api, foundation):
            query = self._query(api, service, account)
            raw = value.encode("utf-8")
            data = foundation.NSData.dataWithBytes_length_(raw, len(raw))
            attributes = {api.kSecValueData: data}
            status = api.SecItemUpdate(query, attributes)
            if status == api.errSecItemNotFound:
                status, _ = api.SecItemAdd({**query, **attributes}, None)
                # 其他进程在 Update 和 Add 之间创建同一条目时，只补一次更新。
                if status == api.errSecDuplicateItem:
                    status = api.SecItemUpdate(query, attributes)
            self._check(status)

    def delete_password(self, service: str, account: str) -> None:
        with self._operation() as (api, _foundation):
            status = api.SecItemDelete(self._query(api, service, account))
            if status != api.errSecItemNotFound:
                self._check(status)


backend = MacOSKeychain()


def access_status() -> dict[str, object]:
    if not enabled():
        return {"supported": False, "blocked": False, "retrying": False, "message": None}
    return backend.status()
