from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field


@dataclass
class AuthStateStore:
    ttl_seconds: int = 600
    _states: dict[str, float] = field(default_factory=dict)

    def issue(self) -> str:
        state = secrets.token_urlsafe(16)
        self._states[state] = time.time() + self.ttl_seconds
        return state

    def consume(self, state: str) -> bool:
        self._purge_expired()
        return self._states.pop(state, None) is not None

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, expires in self._states.items() if expires <= now]
        for key in expired:
            self._states.pop(key, None)
