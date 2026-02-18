from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from src.services.update_service import UpdateAsset, UpdateStatus


class _StubUpdateService:
    def load_cached_status(self) -> UpdateStatus:
        return UpdateStatus(current_version="v0.5.43")

    async def check_for_updates(self, force: bool = False) -> UpdateStatus:
        return UpdateStatus(
            current_version="v0.5.43",
            latest_version="v0.5.44",
            update_available=True,
            asset=UpdateAsset(name="LarkSync-Setup-v0.5.44.exe", url="https://example.com/pkg.exe"),
        )

    async def download_update(self) -> UpdateStatus:
        return UpdateStatus(
            current_version="v0.5.43",
            latest_version="v0.5.44",
            update_available=True,
            asset=UpdateAsset(name="LarkSync-Setup-v0.5.44.exe", url="https://example.com/pkg.exe"),
            download_path="data/updates/LarkSync-Setup-v0.5.44.exe",
        )


class _StubScheduler:
    def __init__(self) -> None:
        self.service = _StubUpdateService()


def test_system_update_endpoints_return_200() -> None:
    client = TestClient(app)
    app.state.update_scheduler = _StubScheduler()

    status_resp = client.get("/system/update/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["current_version"] == "v0.5.43"

    check_resp = client.post("/system/update/check")
    assert check_resp.status_code == 200
    assert check_resp.json()["latest_version"] == "v0.5.44"

    download_resp = client.post("/system/update/download")
    assert download_resp.status_code == 200
    assert download_resp.json()["download_path"]
