from __future__ import annotations

import pytest

from src.services.update_scheduler import UpdateScheduler
from src.services.update_service import UpdateAsset, UpdateStatus


class StubUpdateService:
    def __init__(self, *, auto_enabled: bool, status: UpdateStatus) -> None:
        self._auto_enabled = auto_enabled
        self._status = status
        self.check_calls = 0
        self.download_calls = 0

    def auto_update_enabled(self) -> bool:
        return self._auto_enabled

    async def check_for_updates(self, force: bool = False) -> UpdateStatus:
        self.check_calls += 1
        return self._status

    async def download_update(self) -> UpdateStatus:
        self.download_calls += 1
        payload = self._status.model_copy(deep=True)
        payload.download_path = f"/tmp/{payload.asset.name}" if payload.asset else None
        return payload


@pytest.mark.asyncio
async def test_scheduler_auto_downloads_update_once_per_version() -> None:
    status = UpdateStatus(
        current_version="v0.1.0",
        latest_version="v0.1.1",
        update_available=True,
        asset=UpdateAsset(name="LarkSync-Setup-v0.1.1.exe", url="https://example.com/a.exe"),
    )
    service = StubUpdateService(auto_enabled=True, status=status)
    scheduler = UpdateScheduler(update_service=service)  # type: ignore[arg-type]

    await scheduler._auto_download_if_needed(status)  # noqa: SLF001
    await scheduler._auto_download_if_needed(status)  # noqa: SLF001

    assert service.download_calls == 1


@pytest.mark.asyncio
async def test_scheduler_skips_download_when_auto_update_disabled() -> None:
    status = UpdateStatus(
        current_version="v0.1.0",
        latest_version="v0.1.1",
        update_available=True,
        asset=UpdateAsset(name="LarkSync-Setup-v0.1.1.exe", url="https://example.com/a.exe"),
    )
    service = StubUpdateService(auto_enabled=False, status=status)
    scheduler = UpdateScheduler(update_service=service)  # type: ignore[arg-type]

    await scheduler._auto_download_if_needed(status)  # noqa: SLF001

    assert service.download_calls == 0
