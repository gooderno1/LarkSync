from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import keyring

from .config import ConfigManager


@dataclass(frozen=True)
class TokenData:
    access_token: str
    refresh_token: str
    expires_at: Optional[float]
    open_id: Optional[str] = None
    account_name: Optional[str] = None

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - leeway_seconds)


class TokenStore:
    def get(self) -> Optional[TokenData]:
        raise NotImplementedError

    def set(self, token: TokenData) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class KeyringTokenStore(TokenStore):
    """Windows 凭据管理器单条记录限 2560 字节，拆分存储以避免 CredWrite 1783 错误。"""

    _service = "larksync"
    # 拆分存储的 key
    _KEY_ACCESS = "access_token"
    _KEY_REFRESH = "refresh_token"
    _KEY_EXPIRES = "expires_at"
    _KEY_OPEN_ID = "open_id"
    _KEY_ACCOUNT_NAME = "account_name"
    # 旧版合并存储 key（兼容迁移）
    _KEY_LEGACY = "oauth_tokens"

    def get(self) -> Optional[TokenData]:
        # 优先读取拆分格式
        access_token = keyring.get_password(self._service, self._KEY_ACCESS)
        if access_token:
            refresh_raw = keyring.get_password(self._service, self._KEY_REFRESH) or ""
            refresh_token = "" if refresh_raw == "_empty_" else refresh_raw
            expires_raw = keyring.get_password(self._service, self._KEY_EXPIRES)
            expires_at = float(expires_raw) if expires_raw else None
            open_id_raw = keyring.get_password(self._service, self._KEY_OPEN_ID)
            account_name_raw = keyring.get_password(self._service, self._KEY_ACCOUNT_NAME)
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                open_id=open_id_raw.strip() if open_id_raw else None,
                account_name=account_name_raw.strip() if account_name_raw else None,
            )
        # 回退：读取旧版合并格式
        raw = keyring.get_password(self._service, self._KEY_LEGACY)
        if not raw:
            return None
        data = json.loads(raw)
        return TokenData(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=data.get("expires_at"),
            open_id=data.get("open_id"),
            account_name=data.get("account_name"),
        )

    def set(self, token: TokenData) -> None:
        keyring.set_password(self._service, self._KEY_ACCESS, token.access_token)
        keyring.set_password(
            self._service, self._KEY_REFRESH, token.refresh_token or "_empty_"
        )
        expires_str = str(token.expires_at) if token.expires_at is not None else ""
        if expires_str:
            keyring.set_password(self._service, self._KEY_EXPIRES, expires_str)
        if token.open_id:
            keyring.set_password(self._service, self._KEY_OPEN_ID, token.open_id)
        else:
            try:
                keyring.delete_password(self._service, self._KEY_OPEN_ID)
            except keyring.errors.PasswordDeleteError:
                pass
        if token.account_name:
            keyring.set_password(self._service, self._KEY_ACCOUNT_NAME, token.account_name)
        else:
            try:
                keyring.delete_password(self._service, self._KEY_ACCOUNT_NAME)
            except keyring.errors.PasswordDeleteError:
                pass
        # 清除旧版合并记录（避免数据不一致）
        try:
            keyring.delete_password(self._service, self._KEY_LEGACY)
        except keyring.errors.PasswordDeleteError:
            pass

    def clear(self) -> None:
        for key in (
            self._KEY_ACCESS,
            self._KEY_REFRESH,
            self._KEY_EXPIRES,
            self._KEY_OPEN_ID,
            self._KEY_ACCOUNT_NAME,
            self._KEY_LEGACY,
        ):
            try:
                keyring.delete_password(self._service, key)
            except keyring.errors.PasswordDeleteError:
                pass


class MemoryTokenStore(TokenStore):
    def __init__(self) -> None:
        self._token: Optional[TokenData] = None

    def get(self) -> Optional[TokenData]:
        return self._token

    def set(self, token: TokenData) -> None:
        self._token = token

    def clear(self) -> None:
        self._token = None


def get_token_store() -> TokenStore:
    config = ConfigManager.get().config
    store = os.getenv("LARKSYNC_TOKEN_STORE", config.token_store).lower()
    if store == "memory":
        return MemoryTokenStore()
    return KeyringTokenStore()
