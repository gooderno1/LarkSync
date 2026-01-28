from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field


@dataclass
class AuthStateStore:
    ttl_seconds: int = 600
    _states: dict[str, float] = field(default_factory=dict)
    _redirects: dict[str, str] = field(default_factory=dict)

    def issue(self, redirect_to: str | None = None) -> str:
        state = secrets.token_urlsafe(16)
        self._states[state] = time.time() + self.ttl_seconds
        if redirect_to:
            self._redirects[state] = redirect_to
        return state

    def consume(self, state: str) -> tuple[bool, str | None]:
        self._purge_expired()
        valid = self._states.pop(state, None) is not None
        redirect_to = self._redirects.pop(state, None) if valid else None
        return valid, redirect_to

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, expires in self._states.items() if expires <= now]
        for key in expired:
            self._states.pop(key, None)
            self._redirects.pop(key, None)
