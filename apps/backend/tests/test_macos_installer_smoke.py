import json
import signal
import sys
import threading
import time
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


def test_assert_app_drop_link_requires_system_applications_link(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mount_point = tmp_path / "Volumes" / "LarkSync"
    app_drop_link = mount_point / "Applications"
    mount_point.mkdir(parents=True, exist_ok=True)
    app_drop_link.mkdir()

    monkeypatch.setattr(smoke.os.path, "realpath", lambda path: "/Applications")

    resolved = smoke._assert_app_drop_link(mount_point)

    assert resolved == app_drop_link


def test_assert_app_drop_link_rejects_missing_or_wrong_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mount_point = tmp_path / "Volumes" / "LarkSync"
    mount_point.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="Applications 安装入口"):
        smoke._assert_app_drop_link(mount_point)

    (mount_point / "Applications").mkdir()
    monkeypatch.setattr(smoke.os.path, "realpath", lambda path: "/tmp/not-applications")

    with pytest.raises(RuntimeError, match="安装入口异常"):
        smoke._assert_app_drop_link(mount_point)


def test_run_macos_installer_smoke_installs_and_launches_backend_and_wkwebview(
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
    monkeypatch.setattr(smoke, "_assert_app_drop_link", lambda _mount_point: mount_point / "Applications")
    monkeypatch.setattr(smoke, "_copy_app_bundle", lambda _mount_point, _target_root: copied_app)
    monkeypatch.setattr(smoke, "_assert_bundle_metadata", lambda _app: {"CFBundleShortVersionString": "1.0.0"})
    monkeypatch.setattr(smoke, "_assert_code_signature", lambda _app: None)
    monkeypatch.setattr(smoke, "_run_keychain_smoke", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(smoke, "_wait_for_health", lambda timeout_seconds, **kwargs: None)
    configured: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(smoke, "_put_json", lambda path, payload: configured.append((path, payload)) or {})
    monkeypatch.setattr(
        smoke,
        "_wait_for_gui_result",
        lambda result_path, process, timeout_seconds, **kwargs: {
            "ok": True,
            "onboarding_visible": True,
            "qr_state": "ready",
            "qr_visible": True,
            "qr_is_data_url": True,
        },
    )
    detached: list[Path] = []
    monkeypatch.setattr(smoke, "_detach_dmg", lambda path: detached.append(path))

    captured: dict[str, object] = {"calls": [], "signals": 0}

    class DummyProcess:
        def __init__(self) -> None:
            self._poll = None

        def poll(self):
            return self._poll

        def send_signal(self, sig):
            captured["signal"] = sig
            captured["signals"] = int(captured["signals"]) + 1
            self._poll = 0

        def wait(self, timeout=None):
            captured["wait_timeout"] = timeout
            self._poll = 0
            return 0

        def kill(self):
            captured["killed"] = True
            self._poll = 0

    def fake_popen(args, **kwargs):
        captured["calls"].append((args, kwargs))
        return DummyProcess()

    monkeypatch.setattr(smoke.subprocess, "Popen", fake_popen)

    result = smoke.run_macos_installer_smoke(
        dmg_path=tmp_path / "LarkSync-v1.0.0-arm64.dmg",
        timeout_seconds=5.0,
    )

    assert result["mount_point"] == str(mount_point)
    assert result["app_drop_link"] == str(mount_point / "Applications")
    assert result["app_bundle"] == str(copied_app)
    assert result["stdout_path"].endswith("bundle-stdout.log")
    assert result["stderr_path"].endswith("bundle-stderr.log")
    calls = captured["calls"]
    assert calls[0][0] == [str(copied_exec), "--backend"]
    assert calls[1][0][:7] == [
        "open",
        "-W",
        "-n",
        str(copied_app),
        "--args",
        "--desktop-window",
        "--url",
    ]
    assert "http://127.0.0.1:18765/" in calls[1][0]
    assert "--smoke-result" in calls[1][0]
    kwargs = calls[0][1]
    assert kwargs["env"]["LARKSYNC_BACKEND_BIND_HOST"] == "127.0.0.1"
    assert "LARKSYNC_DATA_DIR" in kwargs["env"]
    assert kwargs["cwd"] == str(copied_app)
    assert kwargs["stdin"] == smoke.subprocess.DEVNULL
    assert captured["signal"] == signal.SIGTERM
    assert captured["signals"] == 2
    assert configured[0][0] == "/config"
    assert configured[0][1]["auth_client_id"] == "cli_macos_smoke"
    assert detached == [mount_point]


def test_assert_bundle_metadata_requires_real_icon(tmp_path: Path) -> None:
    app = tmp_path / "LarkSync.app"
    resources = app / "Contents" / "Resources"
    resources.mkdir(parents=True)
    info = {
        "CFBundleIdentifier": "com.larksync.app",
        "CFBundleDisplayName": "LarkSync",
        "CFBundleName": "LarkSync",
        "CFBundleShortVersionString": "1.2.3",
        "CFBundleIconFile": "LarkSync.icns",
        "NSHighResolutionCapable": True,
    }
    with (app / "Contents" / "Info.plist").open("wb") as stream:
        smoke.plistlib.dump(info, stream)

    with pytest.raises(FileNotFoundError, match="图标无效"):
        smoke._assert_bundle_metadata(app)

    (resources / "LarkSync.icns").write_bytes(b"icns")
    assert smoke._assert_bundle_metadata(app)["CFBundleIdentifier"] == "com.larksync.app"


def test_run_macos_installer_smoke_rejects_non_macos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(smoke.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="仅支持 macOS"):
        smoke.run_macos_installer_smoke(dmg_path=tmp_path / "demo.dmg")


def test_macos_ci_installs_webkit_and_checks_visible_qr_contract() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "release-build.yml").read_text(
        encoding="utf-8"
    )
    webkit_script = (PROJECT_ROOT / "scripts" / "macos_webkit_smoke.mjs").read_text(
        encoding="utf-8"
    )

    assert workflow.count("npx playwright install webkit") == 2
    assert 'webkit.launch({ headless: true })' in webkit_script
    assert 'data-onboarding-root="true"' in webkit_script
    assert 'data-testid="oauth-qr-panel"' in webkit_script
    assert 'data-testid="oauth-qr-image"' in webkit_script
    assert 'data:image/png;base64,' in webkit_script


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

    with pytest.raises(RuntimeError, match="18765 已被占用"):
        smoke._assert_backend_port_available()


def test_build_launch_failure_message_includes_log_tails(tmp_path: Path) -> None:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    data_root = tmp_path / "AppData"
    backend_log = data_root / "logs" / "larksync.log"
    backend_log.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text("stdout-line", encoding="utf-8")
    stderr_path.write_text("stderr-line", encoding="utf-8")
    backend_log.write_text("backend-line", encoding="utf-8")

    class ExitedProcess:
        def poll(self):
            return 3

    message = smoke._build_launch_failure_message(
        "启动失败",
        process=ExitedProcess(),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        data_root=data_root,
        last_error=ConnectionRefusedError(61, "Connection refused"),
    )

    assert "启动失败" in message
    assert "process=exited(3)" in message
    assert "stdout-line" in message
    assert "stderr-line" in message
    assert "backend-line" in message
    assert "ConnectionRefusedError" in message


def test_wait_for_health_reports_early_process_exit(tmp_path: Path) -> None:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")

    class ExitedProcess:
        def poll(self):
            return 9

    with pytest.raises(RuntimeError, match="进程提前退出") as excinfo:
        smoke._wait_for_health(
            1.0,
            process=ExitedProcess(),
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            data_root=tmp_path,
        )

    assert "process=exited(9)" in str(excinfo.value)


def test_wait_for_gui_result_reports_native_logs_on_early_exit(tmp_path: Path) -> None:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    data_root = tmp_path / "AppData"
    bootstrap_log = data_root / "logs" / "bootstrap-error.log"
    stdout_path.write_text("launchservices-out", encoding="utf-8")
    stderr_path.write_text("cocoa-trap", encoding="utf-8")
    bootstrap_log.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_log.write_text("webview-bootstrap", encoding="utf-8")

    class ExitedProcess:
        def poll(self):
            return -5

    with pytest.raises(RuntimeError, match="WKWebView GUI 进程提前退出") as excinfo:
        smoke._wait_for_gui_result(
            tmp_path / "missing.json",
            ExitedProcess(),
            1.0,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            data_root=data_root,
        )

    message = str(excinfo.value)
    assert "process=exited(-5)" in message
    assert "launchservices-out" in message
    assert "cocoa-trap" in message
    assert "webview-bootstrap" in message


def test_wait_for_gui_result_does_not_treat_successful_open_helper_as_app_exit(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "result.json"

    class SuccessfulOpenHelper:
        def poll(self):
            return 0

    def publish_result() -> None:
        time.sleep(0.05)
        result_path.write_text('{"completed": true, "ok": true}', encoding="utf-8")

    threading.Thread(target=publish_result, daemon=True).start()

    payload = smoke._wait_for_gui_result(result_path, SuccessfulOpenHelper(), 1.0)

    assert payload["ok"] is True


def test_wait_for_gui_result_uses_webkit_fallback_for_stable_headless_native_loop(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "completed": False,
                "ok": False,
                "stage": "webview_starting",
                "pid": smoke.os.getpid(),
            }
        ),
        encoding="utf-8",
    )

    class SuccessfulOpenHelper:
        def poll(self):
            return 0

    payload = smoke._wait_for_gui_result(
        result_path,
        SuccessfulOpenHelper(),
        1.0,
        headless_webkit_runner=lambda: {
            "ok": True,
            "qr_state": "ready",
            "qr_visible": True,
        },
        headless_fallback_delay=0.0,
    )

    assert payload["ok"] is True
    assert payload["validation_mode"] == "launchservices-stage+headless-webkit"
    assert payload["native_stage"] == "webview_starting"
    assert payload["native_pid_alive"] is True
    assert payload["webkit"]["qr_state"] == "ready"
