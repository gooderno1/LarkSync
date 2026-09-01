from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


_account_id: ContextVar[str | None] = ContextVar(
    "larksync_account_id",
    default=None,
)


def current_account_id() -> str | None:
    value = _account_id.get()
    if not value:
        return None
    return value


@contextmanager
def account_scope(account_id: str | None) -> Iterator[None]:
    normalized = account_id.strip() if isinstance(account_id, str) else None
    marker = _account_id.set(normalized or None)
    try:
        yield
    finally:
        _account_id.reset(marker)


__all__ = ["account_scope", "current_account_id"]
