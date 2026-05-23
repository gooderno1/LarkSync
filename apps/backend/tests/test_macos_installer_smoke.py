import signal
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import macos_installer_smoke as smoke


def test_find_latest_dmg_prefers_requested_arch_suffix(tmp_path: Path) -> None:
    generic = tmp_path / "LarkSync-v1.0.0.dmg"
    arm = tmp_path / "LarkSync-v1.0.0-arm64.dmg"
    generic.write_bytes(b"generic")
    arm.write_bytes(b"arm")

    selected = smoke._find_latest_dmg(tmp_path, "arm64")

    assert selected == arm


def test_extract_mount_point_from_hdiutil_plist() -> None:
    plist_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>system-entities</key>
  <array>
    <dict>
      <key>mount-point</key>
      <string>/Volumes/LarkSync</string>
    </dict>
  </array>
</dict>
</plist>
"""

    mount_point = smoke._extract_mount_point(plist_bytes)

    assert mount_point == Path("/Volumes/LarkSync")


def test_copy_app_bundle_copies_from_mounted_volume(tmp_path: Path) -> None:
    mount_point = tmp_path / "Volumes" / "LarkSync"
    source_app = mount_point / "LarkSync.app"
    (source_app / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
    (source_app / "Contents" / "MacOS" / "LarkSync").write_text("binary", encoding="utf-8")

    copied = smoke._copy_app_bundle(mount_point, tmp_path / "Applications")

    assert copied == tmp_path / "Applications" / "LarkSync.app"
    assert (copied / "Contents" / "MacOS" / "LarkSync").is_file()


def test_run_macos_installer_smoke_installs_and_launches_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mount_point = tmp_path / "Volumes" / "LarkSync"
    mounted_app = mount_point / "LarkSync.app"
    executable = mounted_app / "Contents" / "MacOS" / "LarkSync"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("binary", encoding="utf-8")
    copied_app = tmp_path / "Applications" / "LarkSync.app"
    copied_exec = copied_app / "Contents" / "MacOS" / "LarkSync"
    copied_exec.parent.mkdir(parents=True, exist_ok=True)
    copied_exec.write_text("binary", encoding="utf-8")

    monkeypatch.setattr(smoke.sys, "platform", "darwin")
    monkeypatch.setattr(smoke, "_assert_backend_port_available", lambda: None)
    monkeypatch.setattr(smoke, "_attach_dmg", lambda dmg_path: mount_point)
    monkeypatch.setattr(smoke, "_copy_app_bundle", lambda _mount_point, _target_root: copied_app)
    monkeypatch.setattr(smoke, "_wait_for_health", lambda timeout_seconds: None)
    detached: list[Path] = []
    monkeypatch.setattr(smoke, "_detach_dmg", lambda path: detached.append(path))

    captured: dict[str, object] = {}

    class DummyProcess:
        def __init__(self) -> None:
            self._poll = None

        def poll(self):
            return self._poll

        def send_signal(self, sig):
            captured["signal"] = sig
            self._poll = 0

        def wait(self, timeout=None):
            captured["wait_timeout"] = timeout
            self._poll = 0
            return 0

        def kill(self):
            captured["killed"] = True
            self._poll = 0

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(smoke.subprocess, "Popen", fake_popen)

    result = smoke.run_macos_installer_smoke(
        dmg_path=tmp_path / "LarkSync-v1.0.0-arm64.dmg",
        timeout_seconds=5.0,
    )

    assert result["mount_point"] == str(mount_point)
    assert result["app_bundle"] == str(copied_app)
    assert captured["args"] == [str(copied_exec), "--backend"]
    kwargs = captured["kwargs"]
    assert kwargs["env"]["LARKSYNC_BACKEND_BIND_HOST"] == "127.0.0.1"
    assert "LARKSYNC_DATA_DIR" in kwargs["env"]
    assert kwargs["cwd"] == str(copied_app)
    assert captured["signal"] == signal.SIGTERM
    assert detached == [mount_point]


def test_run_macos_installer_smoke_rejects_non_macos(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="仅支持 macOS"):
        smoke.run_macos_installer_smoke(dmg_path=tmp_path / "demo.dmg")


def test_assert_backend_port_available_raises_when_port_is_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BusySocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def settimeout(self, timeout):
            return None

        def connect_ex(self, address):
            return 0

    monkeypatch.setattr(smoke.socket, "socket", lambda *args, **kwargs: BusySocket())

    with pytest.raises(RuntimeError, match="8000 已被占用"):
        smoke._assert_backend_port_available()
