from __future__ import annotations

import json

import pytest

from src.services.event_hub import EventHub


class _Socket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict[str, object]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, message: str) -> None:
        self.messages.append(json.loads(message))


@pytest.mark.asyncio
async def test_event_hub_filters_connections_by_account() -> None:
    hub = EventHub()
    socket_a = _Socket()
    socket_b = _Socket()
    await hub.connect(socket_a, account_id="account-a")  # type: ignore[arg-type]
    await hub.connect(socket_b, account_id="account-b")  # type: ignore[arg-type]

    await hub.broadcast({"account_id": "account-a", "status": "uploaded"})

    assert socket_a.messages == [{"account_id": "account-a", "status": "uploaded"}]
    assert socket_b.messages == []


@pytest.mark.asyncio
async def test_event_hub_does_not_send_unscoped_events_to_scoped_connections() -> None:
    hub = EventHub()
    socket = _Socket()
    await hub.connect(socket, account_id="account-a")  # type: ignore[arg-type]

    await hub.broadcast({"status": "changed"})

    assert socket.messages == []
