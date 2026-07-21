from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional

import keyring

from .config import ConfigManager
from .paths import data_dir


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

    def __init__(self) -> None:
        self._cache_lock = RLock()
        self._cache_loaded = False
        self._cached_token: Optional[TokenData] = None

    def get(self) -> Optional[TokenData]:
        with self._cache_lock:
            if self._cache_loaded:
                return self._cached_token
            self._cached_token = self._read_from_keyring()
            self._cache_loaded = True
            return self._cached_token

    def _read_from_keyring(self) -> Optional[TokenData]:
        # 优先读取拆分格式。Windows 凭据管理器属于同步系统调用，只允许首次加载。
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
        with self._cache_lock:
            keyring.set_password(self._service, self._KEY_ACCESS, token.access_token)
            keyring.set_password(
                self._service, self._KEY_REFRESH, token.refresh_token or "_empty_"
            )
            expires_str = str(token.expires_at) if token.expires_at is not None else ""
            if expires_str:
                keyring.set_password(self._service, self._KEY_EXPIRES, expires_str)
            else:
                self._delete_key(self._KEY_EXPIRES)
            if token.open_id:
                keyring.set_password(self._service, self._KEY_OPEN_ID, token.open_id)
            else:
                self._delete_key(self._KEY_OPEN_ID)
            if token.account_name:
                keyring.set_password(self._service, self._KEY_ACCOUNT_NAME, token.account_name)
            else:
                self._delete_key(self._KEY_ACCOUNT_NAME)
            self._delete_key(self._KEY_LEGACY)
            self._cached_token = token
            self._cache_loaded = True

    def _delete_key(self, key: str) -> None:
        try:
            keyring.delete_password(self._service, key)
        except keyring.errors.PasswordDeleteError:
            pass

    def clear(self) -> None:
        with self._cache_lock:
            for key in (
                self._KEY_ACCESS,
                self._KEY_REFRESH,
                self._KEY_EXPIRES,
                self._KEY_OPEN_ID,
                self._KEY_ACCOUNT_NAME,
                self._KEY_LEGACY,
            ):
                self._delete_key(key)
            self._cached_token = None
            self._cache_loaded = True


class MemoryTokenStore(TokenStore):
    def __init__(self) -> None:
        self._token: Optional[TokenData] = None

    def get(self) -> Optional[TokenData]:
        return self._token

    def set(self, token: TokenData) -> None:
        self._token = token

    def clear(self) -> None:
        self._token = None


class FileTokenStore(TokenStore):
    """用于无桌面 keyring 环境（如 WSL/CI）的文件凭证存储。"""

    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("LARKSYNC_TOKEN_FILE")
        target = path
        if target is None and env_path:
            target = Path(env_path).expanduser()
        if target is None:
            target = data_dir() / "token_store.json"
        self._path = target.resolve()

    def get(self) -> Optional[TokenData]:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return None
        refresh_token = payload.get("refresh_token", "")
        if not isinstance(refresh_token, str):
            refresh_token = ""
        expires_raw = payload.get("expires_at")
        expires_at: Optional[float] = None
        if isinstance(expires_raw, (int, float)):
            expires_at = float(expires_raw)
        elif isinstance(expires_raw, str) and expires_raw.strip():
            try:
                expires_at = float(expires_raw)
            except ValueError:
                expires_at = None
        open_id = payload.get("open_id")
        if not isinstance(open_id, str) or not open_id.strip():
            open_id = None
        account_name = payload.get("account_name")
        if not isinstance(account_name, str) or not account_name.strip():
            account_name = None
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            open_id=open_id.strip() if open_id else None,
            account_name=account_name.strip() if account_name else None,
        )

    def set(self, token: TokenData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "open_id": token.open_id,
            "account_name": token.account_name,
        }
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_path, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    def clear(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


_shared_keyring_store: KeyringTokenStore | None = None


def get_token_store() -> TokenStore:
    global _shared_keyring_store
    config = ConfigManager.get().config
    store = os.getenv("LARKSYNC_TOKEN_STORE", config.token_store).lower()
    if store == "memory":
        return MemoryTokenStore()
    if store == "file":
        return FileTokenStore()
    if _shared_keyring_store is None:
        _shared_keyring_store = KeyringTokenStore()
    return _shared_keyring_store
