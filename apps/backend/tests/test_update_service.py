from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.services.update_service import (
    UpdateService,
    compute_file_sha256,
    extract_sha256_from_release_notes,
    extract_sha256_from_text,
    find_checksum_asset,
    is_dev_version,
    is_newer_version,
    parse_sha256_digest_field,
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


def test_parse_sha256_digest_field() -> None:
    digest = "d" * 64
    assert parse_sha256_digest_field(f"sha256:{digest}") == digest
    assert parse_sha256_digest_field(digest.upper()) == digest
    assert parse_sha256_digest_field("sha1:123") is None
    assert parse_sha256_digest_field("invalid") is None


def test_select_asset_reads_github_digest_field() -> None:
    digest = "e" * 64
    assets = [
        {
            "name": "LarkSync-Setup-v0.5.0.exe",
            "browser_download_url": "https://x",
            "size": 123,
            "digest": f"sha256:{digest}",
        }
    ]
    win_asset = select_asset(assets, "win32")
    assert win_asset is not None
    assert win_asset.sha256 == digest


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


def test_extract_sha256_from_release_notes_markdown_table() -> None:
    digest = "b" * 64
    notes = (
        "| asset | sha256 |\n"
        "|---|---|\n"
        f"| LarkSync-Setup-v0.5.0.exe | `{digest}` |\n"
    )
    assert (
        extract_sha256_from_release_notes(notes, "LarkSync-Setup-v0.5.0.exe")
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


@pytest.mark.asyncio
async def test_check_for_updates_uses_release_notes_sha256_when_no_checksum_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest = "c" * 64
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"auto_update_enabled": true, "update_check_interval_hours": 24, "allow_dev_to_stable": true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    service = UpdateService(config_manager=ConfigManager.get())
    service._status_path = tmp_path / "status.json"  # type: ignore[attr-defined]

    async def fake_fetch_latest_release():
        return {
            "tag_name": "v9.9.9",
            "body": (
                "| asset | sha256 |\n"
                "|---|---|\n"
                f"| LarkSync-Setup-v9.9.9.exe | `{digest}` |\n"
            ),
            "published_at": "2026-03-07T00:00:00Z",
            "assets": [
                {
                    "name": "LarkSync-Setup-v9.9.9.exe",
                    "browser_download_url": "https://example.com/LarkSync-Setup-v9.9.9.exe",
                    "size": 123,
                }
            ],
        }

    monkeypatch.setattr(service, "_fetch_latest_release", fake_fetch_latest_release)
    monkeypatch.setattr("src.services.update_service.sys.platform", "win32")

    status = await service.check_for_updates(force=True)

    assert status.update_available is True
    assert status.asset is not None
    assert status.asset.checksum_url is None
    assert status.asset.sha256 == digest
