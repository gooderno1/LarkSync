import sys
from pathlib import Path

import pytest
import httpx

from src.core.config import ConfigManager
from src.core.paths import update_data_dir
from src.services.update_service import (
    UpdateService,
    compute_file_sha256,
    extract_sha256_from_release_notes,
    extract_sha256_from_text,
    extract_installer_version,
    find_checksum_asset,
    is_dev_version,
    is_newer_version,
    parse_sha256_digest_field,
    release_asset_name_for_platform,
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


def test_select_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    assets = [
        {"name": "LarkSync-Setup-v0.5.0.exe", "browser_download_url": "https://x", "size": 123},
        {"name": "LarkSync-v0.5.0-x86_64.dmg", "browser_download_url": "https://intel", "size": 456},
        {"name": "LarkSync-v0.5.0-arm64.dmg", "browser_download_url": "https://arm", "size": 456},
    ]
    monkeypatch.setattr("src.services.update_service.platform.machine", lambda: "arm64")
    win_asset = select_asset(assets, "win32")
    mac_asset = select_asset(assets, "darwin")

    assert win_asset is not None
    assert win_asset.name.endswith(".exe")
    assert mac_asset is not None
    assert mac_asset.name.endswith("-arm64.dmg")


def test_select_asset_falls_back_to_universal2_then_generic_for_mac(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.update_service.platform.machine", lambda: "arm64")

    universal_assets = [
        {"name": "LarkSync-v0.5.0-universal2.dmg", "browser_download_url": "https://uni", "size": 456},
        {"name": "LarkSync-v0.5.0-x86_64.dmg", "browser_download_url": "https://intel", "size": 456},
    ]
    generic_assets = [
        {"name": "LarkSync-v0.5.0.dmg", "browser_download_url": "https://generic", "size": 456},
        {"name": "LarkSync-v0.5.0-x86_64.dmg", "browser_download_url": "https://intel", "size": 456},
    ]

    universal_asset = select_asset(universal_assets, "darwin")
    generic_asset = select_asset(generic_assets, "darwin")

    assert universal_asset is not None
    assert universal_asset.name.endswith("-universal2.dmg")
    assert generic_asset is not None
    assert generic_asset.name == "LarkSync-v0.5.0.dmg"


def test_parse_sha256_digest_field() -> None:
    digest = "d" * 64
    assert parse_sha256_digest_field(f"sha256:{digest}") == digest
    assert parse_sha256_digest_field(digest.upper()) == digest
    assert parse_sha256_digest_field("sha1:123") is None
    assert parse_sha256_digest_field("invalid") is None


def test_extract_installer_version_from_download_path() -> None:
    assert (
        extract_installer_version(r"C:\Users\me\LarkSync-Setup-v0.6.10.exe")
        == "v0.6.10"
    )
    assert extract_installer_version("LarkSync-Setup-0.6.11-dev.1.exe") == "v0.6.11-dev.1"
    assert extract_installer_version("/Users/me/Downloads/LarkSync-v0.6.12.dmg") == "v0.6.12"
    assert extract_installer_version("/Users/me/Downloads/LarkSync-v0.6.12-arm64.dmg") == "v0.6.12"
    assert extract_installer_version("LarkSync-0.6.13-dev.2.dmg") == "v0.6.13-dev.2"
    assert extract_installer_version("not-larksync.exe") is None


def test_release_asset_name_for_platform_prefers_macos_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.update_service.platform.machine", lambda: "arm64")

    assert release_asset_name_for_platform("v0.6.12", "darwin") == "LarkSync-v0.6.12-arm64.dmg"
    assert release_asset_name_for_platform("v0.6.12", "win32") == "LarkSync-Setup-v0.6.12.exe"


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


@pytest.mark.asyncio
async def test_fetch_latest_release_falls_back_to_public_redirect_on_api_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    class FakeAsyncClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, url: str, **kwargs):
            follow_redirects = bool(kwargs.get("follow_redirects"))
            calls.append((url, follow_redirects))
            request = httpx.Request("GET", url)
            if url.startswith("https://api.github.com/"):
                return httpx.Response(
                    403,
                    json={"message": "API rate limit exceeded"},
                    request=request,
                )
            return httpx.Response(
                302,
                headers={
                    "Location": "https://github.com/gooderno1/LarkSync/releases/tag/v9.9.9"
                },
                request=request,
            )

    monkeypatch.setattr("src.services.update_service.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("src.services.update_service.sys.platform", "win32")

    release = await UpdateService()._fetch_latest_release()

    assert release is not None
    assert release["tag_name"] == "v9.9.9"
    assert release["assets"][0]["name"] == "LarkSync-Setup-v9.9.9.exe"
    assert release["assets"][0]["browser_download_url"].endswith(
        "/releases/download/v9.9.9/LarkSync-Setup-v9.9.9.exe"
    )
    assert release["assets"][1]["name"] == "LarkSync-Setup-v9.9.9.exe.sha256"
    assert calls == [
        ("https://api.github.com/repos/gooderno1/LarkSync/releases/latest", False),
        ("https://github.com/gooderno1/LarkSync/releases/latest", False),
    ]


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


@pytest.mark.asyncio
async def test_check_for_updates_preserves_valid_cached_download_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"auto_update_enabled": true, "update_check_interval_hours": 24, "allow_dev_to_stable": true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    installer = tmp_path / "LarkSync-Setup-v9.9.9.exe"
    installer.write_bytes(b"verified-installer")
    digest = compute_file_sha256(installer)

    service = UpdateService(config_manager=ConfigManager.get())
    service._status_path = tmp_path / "status.json"  # type: ignore[attr-defined]
    service._status_path.write_text(  # type: ignore[attr-defined]
        (
            "{"
            '"current_version":"v0.7.8",'
            '"latest_version":"v9.9.9",'
            '"update_available":true,'
            f'"download_path":"{installer.as_posix()}"'
            "}"
        ),
        encoding="utf-8",
    )

    async def fake_fetch_latest_release():
        return {
            "tag_name": "v9.9.9",
            "body": "",
            "published_at": "2026-05-15T00:00:00Z",
            "assets": [
                {
                    "name": "LarkSync-Setup-v9.9.9.exe",
                    "browser_download_url": "https://example.com/LarkSync-Setup-v9.9.9.exe",
                    "size": installer.stat().st_size,
                    "digest": f"sha256:{digest}",
                }
            ],
        }

    monkeypatch.setattr(service, "_fetch_latest_release", fake_fetch_latest_release)
    monkeypatch.setattr("src.services.update_service.sys.platform", "win32")

    status = await service.check_for_updates(force=True)

    assert status.update_available is True
    assert status.download_path == str(installer)
    assert service.load_cached_status().download_path == str(installer)


def test_load_cached_status_overrides_stale_current_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    service = UpdateService(config_manager=ConfigManager.get())
    service._status_path = tmp_path / "status.json"  # type: ignore[attr-defined]
    service._status_path.write_text(  # type: ignore[attr-defined]
        (
            '{'
            '"current_version":"v0.6.0",'
            '"latest_version":"v0.6.1",'
            '"update_available":true,'
            '"download_path":"data/updates/LarkSync-Setup-v0.6.1.exe"'
            '}'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.services.update_service.get_version", lambda: "v0.6.1")

    status = service.load_cached_status()

    assert status.current_version == "v0.6.1"
    assert status.update_available is False
    assert status.download_path is None


def test_load_cached_status_drops_stale_download_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    old_installer = tmp_path / "LarkSync-Setup-v0.6.9.exe"
    old_installer.write_bytes(b"old")
    service = UpdateService(config_manager=ConfigManager.get())
    service._status_path = tmp_path / "status.json"  # type: ignore[attr-defined]
    service._status_path.write_text(  # type: ignore[attr-defined]
        (
            "{"
            '"current_version":"v0.6.9",'
            '"latest_version":"v0.6.10",'
            '"update_available":true,'
            f'"download_path":"{old_installer.as_posix()}"'
            "}"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.services.update_service.get_version", lambda: "v0.6.9")

    status = service.load_cached_status()

    assert status.update_available is True
    assert status.latest_version == "v0.6.10"
    assert status.download_path is None


def test_update_service_uses_external_update_dir_when_frozen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.delenv("LARKSYNC_UPDATE_ROOT", raising=False)
    monkeypatch.delenv("LARKSYNC_DATA_DIR", raising=False)
    if sys.platform == "win32":
        expected_root = tmp_path / "appdata" / "LarkSync"
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    elif sys.platform == "darwin":
        home_dir = tmp_path / "home"
        expected_root = home_dir / "Library" / "Application Support" / "LarkSync"
        monkeypatch.setenv("HOME", str(home_dir))
    else:
        xdg_data_home = tmp_path / "xdg-data"
        expected_root = xdg_data_home / "LarkSync"
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))
    monkeypatch.setattr("src.core.paths.sys.frozen", True, raising=False)
    ConfigManager.reset()

    service = UpdateService(config_manager=ConfigManager.get())

    assert service._status_path == update_data_dir() / "status.json"  # type: ignore[attr-defined]
    assert service._status_path == expected_root / "updates" / "status.json"  # type: ignore[attr-defined]
