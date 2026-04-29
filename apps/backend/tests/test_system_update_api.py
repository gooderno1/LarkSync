from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api import system as system_api
from src.main import app
from src.services.update_install_service import load_install_request
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


def test_system_update_install_endpoint_writes_install_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path / "data"))
    installer_path = tmp_path / "LarkSync-Setup-v0.5.51.exe"
    installer_path.write_bytes(b"exe")
    restart_path = tmp_path / "LarkSync.exe"
    restart_path.write_bytes(b"exe")
    monkeypatch.setattr(system_api.sys, "frozen", True, raising=False)
    monkeypatch.setattr(system_api.sys, "executable", str(restart_path))

    client = TestClient(app)
    app.state.update_scheduler = _StubScheduler()

    response = client.post(
        "/system/update/install",
        json={"download_path": str(installer_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] is True
    assert Path(payload["installer_path"]) == installer_path.resolve()
    assert payload["silent"] is True
    assert Path(payload["restart_path"]) == restart_path.resolve()

    request = load_install_request()
    assert request is not None
    assert request.request_id
    assert Path(request.installer_path) == installer_path.resolve()
    assert request.silent is True
    assert Path(request.restart_path) == restart_path.resolve()
