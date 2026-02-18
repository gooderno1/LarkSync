from __future__ import annotations

from src.core import device


def _reset_cache() -> None:
    device.current_device_id.cache_clear()
    device.current_device_name.cache_clear()


def test_current_device_id_prefers_env_override(monkeypatch, tmp_path) -> None:
    _reset_cache()
    monkeypatch.setenv("LARKSYNC_DEVICE_ID", "  custom-device  ")
    monkeypatch.setattr(device, "_machine_fingerprint", lambda: "machine-guid")
    monkeypatch.setattr(device, "_device_id_path", lambda: tmp_path / ".device_id")

    assert device.current_device_id() == "custom-device"


def test_current_device_id_uses_machine_fingerprint(monkeypatch, tmp_path) -> None:
    _reset_cache()
    monkeypatch.delenv("LARKSYNC_DEVICE_ID", raising=False)
    monkeypatch.setattr(device, "_machine_fingerprint", lambda: "machine-guid")
    marker = tmp_path / ".device_id"
    monkeypatch.setattr(device, "_device_id_path", lambda: marker)

    got = device.current_device_id()
    assert got == device._fingerprint_to_device_id("machine-guid")
    assert not marker.exists()


def test_current_device_id_falls_back_to_file_storage(monkeypatch, tmp_path) -> None:
    _reset_cache()
    monkeypatch.delenv("LARKSYNC_DEVICE_ID", raising=False)
    monkeypatch.setattr(device, "_machine_fingerprint", lambda: None)
    marker = tmp_path / ".device_id"
    monkeypatch.setattr(device, "_device_id_path", lambda: marker)

    first = device.current_device_id()
    assert first.startswith("dev-")
    assert marker.read_text(encoding="utf-8") == first

    _reset_cache()
    second = device.current_device_id()
    assert second == first


def test_current_device_name_prefers_env_override(monkeypatch) -> None:
    _reset_cache()
    monkeypatch.setenv("LARKSYNC_DEVICE_NAME", "  我的设备  ")
    monkeypatch.setenv("COMPUTERNAME", "pc-name")

    assert device.current_device_name() == "我的设备"


def test_current_device_name_uses_hostname(monkeypatch) -> None:
    _reset_cache()
    monkeypatch.delenv("LARKSYNC_DEVICE_NAME", raising=False)
    monkeypatch.setenv("COMPUTERNAME", "pc-name")

    assert device.current_device_name() == "pc-name"
