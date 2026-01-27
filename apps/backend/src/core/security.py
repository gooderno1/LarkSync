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
    _service = "larksync"
    _username = "oauth_tokens"

    def get(self) -> Optional[TokenData]:
        raw = keyring.get_password(self._service, self._username)
        if not raw:
            return None
        data = json.loads(raw)
        return TokenData(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data.get("expires_at"),
        )

    def set(self, token: TokenData) -> None:
        payload = json.dumps(
            {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at,
            }
        )
        keyring.set_password(self._service, self._username, payload)

    def clear(self) -> None:
        try:
            keyring.delete_password(self._service, self._username)
        except keyring.errors.PasswordDeleteError:
            return


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
