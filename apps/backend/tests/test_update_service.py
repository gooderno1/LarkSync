from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.services.update_service import (
    UpdateService,
    compute_file_sha256,
    extract_sha256_from_text,
    find_checksum_asset,
    is_dev_version,
    is_newer_version,
    select_asset,
)


def test_is_dev_version() -> None:
    assert is_dev_version("v0.5.0-dev.3") is True
    assert is_dev_version("0.5.0") is False


def test_is_newer_version_with_dev() -> None:
    assert is_newer_version("v0.5.0", "v0.5.0-dev.3") is True
    assert is_newer_version("v0.5.1", "v0.5.0") is True
    assert is_newer_version("v0.5.0-dev.2", "v0.5.0-dev.3") is False
    assert is_newer_version("v0.5.0", "v0.5.0") is False


def test_select_asset() -> None:
    assets = [
        {"name": "LarkSync-Setup-v0.5.0.exe", "browser_download_url": "https://x", "size": 123},
        {"name": "LarkSync-v0.5.0.dmg", "browser_download_url": "https://y", "size": 456},
    ]
    win_asset = select_asset(assets, "win32")
    mac_asset = select_asset(assets, "darwin")

    assert win_asset is not None
    assert win_asset.name.endswith(".exe")
    assert mac_asset is not None
    assert mac_asset.name.endswith(".dmg")


def test_find_checksum_asset() -> None:
    assets = [
        {"name": "LarkSync-Setup-v0.5.0.exe", "browser_download_url": "https://x"},
        {
            "name": "LarkSync-Setup-v0.5.0.exe.sha256",
            "browser_download_url": "https://x.sha256",
        },
    ]
    checksum = find_checksum_asset(assets, "LarkSync-Setup-v0.5.0.exe")
    assert checksum is not None
    assert checksum.url == "https://x.sha256"


def test_extract_sha256_from_text() -> None:
    digest = "a" * 64
    text = f"{digest}  LarkSync-Setup-v0.5.0.exe\n"
    assert (
        extract_sha256_from_text(text, "LarkSync-Setup-v0.5.0.exe")
        == digest
    )


def test_compute_file_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "demo.bin"
    file_path.write_bytes(b"hello")
    assert (
        compute_file_sha256(file_path)
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


@pytest.mark.asyncio
async def test_check_for_updates_handles_no_release_without_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"auto_update_enabled": true, "update_check_interval_hours": 24}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    service = UpdateService(config_manager=ConfigManager.get())
    service._status_path = tmp_path / "status.json"  # type: ignore[attr-defined]

    async def fake_fetch_latest_release():
        return None

    monkeypatch.setattr(service, "_fetch_latest_release", fake_fetch_latest_release)
    status = await service.check_for_updates(force=True)

    assert status.update_available is False
    assert status.latest_version is None
    assert status.last_error is None
