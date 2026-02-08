from src.services.update_service import is_dev_version, is_newer_version, select_asset


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
