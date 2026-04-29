from pathlib import Path
import sys
import base64

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import tray_app


class _DummyBackend:
    def maybe_auto_restart(self) -> bool:
        return False


def _build_tray() -> tray_app.LarkSyncTray:
    tray = object.__new__(tray_app.LarkSyncTray)
    tray._backend = _DummyBackend()
    tray._running = True
    tray._icon = None
    tray._dev_mode = False
    tray._current_state = "idle"
    tray._global_paused = False
    tray._last_conflict_count = 0
    return tray


def test_tray_skips_fresh_install_request(monkeypatch, tmp_path: Path) -> None:
    requested_path = tmp_path / "LarkSync-Setup-v0.5.53.exe"
    requested_path.write_bytes(b"exe")
    consumed: list[str] = []
    stopped: list[bool] = []

    tray = _build_tray()

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {
            "installer_path": str(requested_path),
            "created_at": 100.0,
        },
    )
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("cleared"))
    monkeypatch.setattr(
        tray,
        "_schedule_installer_launch",
        lambda path: consumed.append(str(path)),
    )
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))
    monkeypatch.setattr(tray_app.time, "time", lambda: 101.0)

    handled = tray._handle_pending_install_request()

    assert handled is False
    assert consumed == []
    assert stopped == []


def test_tray_processes_mature_install_request_and_stops(monkeypatch, tmp_path: Path) -> None:
    requested_path = tmp_path / "LarkSync-Setup-v0.5.51.exe"
    requested_path.write_bytes(b"exe")
    restart_path = tmp_path / "LarkSync.exe"
    restart_path.write_bytes(b"exe")
    consumed: list[str] = []
    stopped: list[bool] = []

    tray = _build_tray()

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {
            "request_id": "req-1",
            "installer_path": str(requested_path),
            "created_at": 100.0,
            "silent": True,
            "restart_path": str(restart_path),
        },
    )
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("cleared"))
    monkeypatch.setattr(
        tray,
        "_schedule_installer_launch",
        lambda path, *, silent=False, restart_path=None, request_id="": consumed.append(
            f"{path}|silent={silent}|restart={restart_path}|request_id={request_id}"
        ),
    )
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))
    monkeypatch.setattr(tray_app.time, "time", lambda: 103.0)

    handled = tray._handle_pending_install_request()

    assert handled is True
    assert consumed == [
        f"{requested_path}|silent=True|restart={restart_path}|request_id=req-1",
        "cleared",
    ]
    assert stopped == [True]


def test_tray_clears_invalid_install_request_without_stopping(monkeypatch, tmp_path: Path) -> None:
    requested_path = tmp_path / "missing-setup.exe"
    consumed: list[str] = []
    stopped: list[bool] = []
    notifications: list[tuple[tuple[object, ...], dict[str, object]]] = []

    tray = _build_tray()

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {
            "request_id": "req-invalid",
            "installer_path": str(requested_path),
            "created_at": 100.0,
            "silent": True,
        },
    )
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("cleared"))
    monkeypatch.setattr(tray_app, "_append_install_launch_log", lambda message: consumed.append(message))
    monkeypatch.setattr(
        tray,
        "_schedule_installer_launch",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            FileNotFoundError(f"安装包不存在: {requested_path.resolve()}")
        ),
    )
    monkeypatch.setattr(
        tray,
        "_notify",
        lambda *args, **kwargs: notifications.append((args, kwargs)),
    )
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))
    monkeypatch.setattr(tray_app.time, "time", lambda: 103.0)

    handled = tray._handle_pending_install_request()

    assert handled is False
    assert stopped == []
    assert consumed[0].startswith("准备启动安装包:")
    assert consumed[1].startswith("启动安装包失败:")
    assert consumed[2:] == ["cleared"]
    assert notifications


def test_build_windows_installer_launch_command_uses_encoded_command(tmp_path: Path) -> None:
    installer_path = tmp_path / "中文 路径" / "LarkSync's Setup.exe"
    restart_path = tmp_path / "LarkSync.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"
    command = tray_app._build_windows_installer_launch_command(
        installer_path,
        silent=True,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-123",
    )

    assert command[0].lower().endswith("powershell.exe") or command[0].lower() == "powershell"
    assert "-EncodedCommand" in command
    encoded = command[command.index("-EncodedCommand") + 1]
    script = base64.b64decode(encoded).decode("utf-16le")

    assert "Start-Process -LiteralPath $installerPath -ArgumentList $argumentList -PassThru" in script
    assert "$argumentList += '/S'" in script
    assert "Wait-Process -Id $process.Id" in script
    assert str(handoff_path).replace("'", "''") in script
    assert "request_id=req-123" not in script
    assert "req-123" in script
    assert "installer_started" in script
    assert "install_failed" in script
    assert "LarkSync''s Setup.exe" in script
    assert str(restart_path).replace("'", "''") in script
    assert str(log_path).replace("'", "''") in script


def test_schedule_installer_launch_on_windows_uses_detached_powershell(
    monkeypatch, tmp_path: Path
) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.55.exe"
    installer_path.write_bytes(b"exe")
    calls: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        calls.append({"args": list(args), **kwargs})
        class _DummyProc:
            pid = 1234
        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "win32")
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(tray_app, "_wait_for_install_handoff", lambda *args, **kwargs: {"stage": "helper_started"})

    tray = _build_tray()
    tray._schedule_installer_launch(str(installer_path), silent=True, request_id="req-1")

    assert len(calls) == 1
    assert "-EncodedCommand" in calls[0]["args"]
    assert calls[0]["close_fds"] is True


def test_schedule_installer_launch_on_windows_silent_requires_helper_handoff(
    monkeypatch, tmp_path: Path
) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.55.exe"
    installer_path.write_bytes(b"exe")

    def _fake_popen(args, **kwargs):
        class _DummyProc:
            pid = 1234
        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "win32")
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        tray_app,
        "_wait_for_install_handoff",
        lambda *args, **kwargs: {"stage": "launch_failed", "message": "UAC canceled"},
    )

    tray = _build_tray()

    try:
        tray._schedule_installer_launch(str(installer_path), silent=True, request_id="req-2")
    except RuntimeError as exc:
        assert "UAC canceled" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_schedule_installer_launch_on_windows_prefers_startfile(
    monkeypatch, tmp_path: Path
) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.57.exe"
    installer_path.write_bytes(b"exe")
    startfile_calls: list[str] = []
    popen_calls: list[list[str]] = []

    def _fake_startfile(path: str, operation: str | None = None) -> None:
        startfile_calls.append(path)

    def _fake_popen(args, **kwargs):
        popen_calls.append(list(args))
        class _DummyProc:
            pid = 4321
        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "win32")
    monkeypatch.setattr(tray_app.os, "startfile", _fake_startfile, raising=False)
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)

    tray = _build_tray()
    tray._schedule_installer_launch(str(installer_path))

    assert startfile_calls == [str(installer_path.resolve())]
    assert popen_calls == []


def test_schedule_installer_launch_on_windows_falls_back_when_startfile_fails(
    monkeypatch, tmp_path: Path
) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.57.exe"
    installer_path.write_bytes(b"exe")
    startfile_calls: list[str] = []
    popen_calls: list[dict[str, object]] = []

    def _fake_startfile(path: str, operation: str | None = None) -> None:
        startfile_calls.append(path)
        raise OSError("shell execute failed")

    def _fake_popen(args, **kwargs):
        popen_calls.append({"args": list(args), **kwargs})
        class _DummyProc:
            pid = 5678
        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "win32")
    monkeypatch.setattr(tray_app.os, "startfile", _fake_startfile, raising=False)
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)

    tray = _build_tray()
    tray._schedule_installer_launch(str(installer_path))

    assert startfile_calls == [str(installer_path.resolve())]
    assert len(popen_calls) == 1
    assert "-EncodedCommand" in popen_calls[0]["args"]
