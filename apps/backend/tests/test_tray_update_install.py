import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

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
    monkeypatch.setattr(tray_app, "_read_current_app_version", lambda: "v0.5.52")
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
    monkeypatch.setattr(tray_app, "_read_current_app_version", lambda: "v0.5.50")
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
    monkeypatch.setattr(tray_app, "_read_current_app_version", lambda: "v0.5.50")
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


def test_tray_clears_stale_install_request_for_same_version(monkeypatch, tmp_path: Path) -> None:
    requested_path = tmp_path / "LarkSync-Setup-v0.6.7.exe"
    requested_path.write_bytes(b"exe")
    consumed: list[str] = []
    stopped: list[bool] = []

    tray = _build_tray()

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {
            "request_id": "req-stale",
            "installer_path": str(requested_path),
            "created_at": 100.0,
            "silent": True,
        },
    )
    monkeypatch.setattr(tray_app, "_read_current_app_version", lambda: "v0.6.7")
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("request-cleared"))
    monkeypatch.setattr(tray_app, "_clear_install_handoff", lambda: consumed.append("handoff-cleared"))
    monkeypatch.setattr(tray_app, "_append_install_launch_log", lambda message: consumed.append(message))
    monkeypatch.setattr(tray, "_schedule_installer_launch", lambda *args, **kwargs: consumed.append("scheduled"))
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))

    handled = tray._handle_pending_install_request()

    assert handled is False
    assert "scheduled" not in consumed
    assert consumed[0].startswith("忽略过期安装请求:")
    assert consumed[1:] == ["request-cleared", "handoff-cleared"]
    assert stopped == []


def test_tray_clears_stale_install_request_for_same_version_macos_dmg(
    monkeypatch,
    tmp_path: Path,
) -> None:
    requested_path = tmp_path / "LarkSync-v0.6.7.dmg"
    requested_path.write_bytes(b"dmg")
    consumed: list[str] = []
    stopped: list[bool] = []

    tray = _build_tray()

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {
            "request_id": "req-stale-mac",
            "installer_path": str(requested_path),
            "created_at": 100.0,
            "silent": False,
        },
    )
    monkeypatch.setattr(tray_app, "_read_current_app_version", lambda: "v0.6.7")
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("request-cleared"))
    monkeypatch.setattr(tray_app, "_clear_install_handoff", lambda: consumed.append("handoff-cleared"))
    monkeypatch.setattr(tray_app, "_append_install_launch_log", lambda message: consumed.append(message))
    monkeypatch.setattr(tray, "_schedule_installer_launch", lambda *args, **kwargs: consumed.append("scheduled"))
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))

    handled = tray._handle_pending_install_request()

    assert handled is False
    assert "scheduled" not in consumed
    assert consumed[0].startswith("忽略过期安装请求:")
    assert consumed[1:] == ["request-cleared", "handoff-cleared"]
    assert stopped == []


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

    assert "Start-Process -FilePath $installerPath -ArgumentList $argumentList -PassThru" in script
    assert "Start-Process -LiteralPath $installerPath" not in script
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


def test_read_install_handoff_accepts_utf8_bom(monkeypatch, tmp_path: Path) -> None:
    handoff_path = tmp_path / "install-handoff.json"
    payload = {"request_id": "req-bom", "stage": "helper_started"}
    handoff_path.write_text(json.dumps(payload), encoding="utf-8-sig")

    monkeypatch.setattr(tray_app, "_install_handoff_path", lambda: handoff_path)

    assert tray_app._read_install_handoff() == payload


def test_wait_for_ready_install_handoff_skips_bootstrap_stage(monkeypatch) -> None:
    payloads = iter(
        [
            {"request_id": "req-ready", "stage": "bootstrap_started", "message": "worker_pid=1234"},
            {"request_id": "req-ready", "stage": "helper_started", "message": "helper process started"},
        ]
    )
    timestamps = iter([0.0, 0.1, 0.2, 0.3, 0.4])

    monkeypatch.setattr(tray_app, "_read_install_handoff", lambda: next(payloads))
    monkeypatch.setattr(tray_app.time, "time", lambda: next(timestamps))
    monkeypatch.setattr(tray_app.time, "sleep", lambda *_args, **_kwargs: None)

    handoff = tray_app._wait_for_ready_install_handoff("req-ready", timeout=1.0)

    assert handoff == {
        "request_id": "req-ready",
        "stage": "helper_started",
        "message": "helper process started",
    }


def test_build_windows_installer_worker_verifies_version_and_retries_restart(tmp_path: Path) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.58.exe"
    restart_path = tmp_path / "LarkSync.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"

    script = tray_app._build_windows_installer_worker_script(
        installer_path,
        silent=True,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-restart",
    )

    assert "Read-InstalledVersion" in script
    assert "Test-ExpectedVersionInstalled" in script
    assert "if ($null -eq $exitCode)" in script
    assert "安装后版本复核" in script
    assert "Start-RestartTarget" in script
    assert "attempt=" in script
    assert "重启进程过早退出" in script
    assert "restart_succeeded" in script
    assert "restart_failed" in script
    assert "exit_code=<null>" in script


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows")
def test_generated_powershell_scripts_use_utf8_bom_on_windows(tmp_path: Path) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.58.exe"
    restart_path = tmp_path / "LarkSync.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"
    script_dir = tmp_path / "install-scripts"

    command = tray_app._build_windows_silent_bootstrap_command(
        installer_path,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-bom-script",
        script_dir=script_dir,
    )
    bootstrap_path = Path(command[command.index("-File") + 1])
    worker_path = next(script_dir.glob("*worker*.ps1"))

    assert bootstrap_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert worker_path.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows PowerShell")
def test_generated_worker_script_runs_under_windows_powershell(tmp_path: Path) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.58.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"
    script_path = tmp_path / "worker.ps1"

    script = tray_app._build_windows_installer_worker_script(
        installer_path,
        silent=True,
        restart_path=None,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-ps51",
    )
    tray_app._write_powershell_script(script_path, script)

    result = subprocess.run(
        [
            tray_app._resolve_powershell_executable(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "ParserError" not in (result.stderr or "")

    payload = json.loads(handoff_path.read_text(encoding="utf-8-sig"))
    assert payload["request_id"] == "req-ps51"
    assert payload["stage"] == "launch_failed"


def test_windows_handoff_scripts_write_json_without_bom(tmp_path: Path) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.58.exe"
    restart_path = tmp_path / "LarkSync.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"
    script_dir = tmp_path / "install-scripts"

    command = tray_app._build_windows_silent_bootstrap_command(
        installer_path,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-utf8",
        script_dir=script_dir,
    )
    bootstrap_path = Path(command[command.index("-File") + 1])
    worker_path = next(script_dir.glob("*worker*.ps1"))
    bootstrap_script = bootstrap_path.read_text(encoding="utf-8")
    worker_script = worker_path.read_text(encoding="utf-8")

    assert "[System.Text.UTF8Encoding]::new($false)" in bootstrap_script
    assert "[System.Text.UTF8Encoding]::new($false)" in worker_script
    assert "Set-Content -LiteralPath $handoffPath -Value $payload -Encoding UTF8" not in bootstrap_script
    assert "Set-Content -LiteralPath $handoffPath -Value $payload -Encoding UTF8" not in worker_script


def test_build_windows_silent_bootstrap_command_uses_script_files(tmp_path: Path) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.56.exe"
    restart_path = tmp_path / "LarkSync.exe"
    log_path = tmp_path / "update-install.log"
    handoff_path = tmp_path / "install-handoff.json"
    script_dir = tmp_path / "install-scripts"
    command = tray_app._build_windows_silent_bootstrap_command(
        installer_path,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id="req-bootstrap",
        script_dir=script_dir,
    )

    assert command[0].lower().endswith("powershell.exe") or command[0].lower() == "powershell"
    assert "-EncodedCommand" not in command
    assert "-File" in command
    bootstrap_path = Path(command[command.index("-File") + 1])
    assert bootstrap_path.is_file()

    script = bootstrap_path.read_text(encoding="utf-8")
    worker_files = list(script_dir.glob("*worker*.ps1"))
    assert len(worker_files) == 1
    worker_script = worker_files[0].read_text(encoding="utf-8")

    assert "Start-Process -FilePath $powerShellPath -ArgumentList $workerArgs -WindowStyle Hidden -PassThru" in script
    assert "'-File', $workerPath" in script
    assert "bootstrap_started" in script
    assert "worker_pid=" in script
    assert "workerEncoded" not in script
    assert "Start-Process -FilePath $installerPath -ArgumentList $argumentList -PassThru" in worker_script
    assert "installer_started" in worker_script
    assert "helper_started" in worker_script
    assert str(handoff_path).replace("'", "''") in script
    assert str(log_path).replace("'", "''") in script


def test_launch_hidden_helper_process_falls_back_when_breakaway_launch_denied(monkeypatch) -> None:
    create_new_process_group = 0x200
    create_no_window = 0x08000000
    create_breakaway = 0x01000000
    calls: list[int] = []
    notices: list[str] = []

    class _DummyProc:
        pid = 9876

    def _fake_popen(args, **kwargs):
        creationflags = int(kwargs.get("creationflags", 0))
        calls.append(creationflags)
        if creationflags == (create_new_process_group | create_no_window | create_breakaway):
            raise PermissionError(5, "Access is denied")
        return _DummyProc()

    monkeypatch.setattr(
        tray_app.subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_process_group, raising=False
    )
    monkeypatch.setattr(tray_app.subprocess, "CREATE_NO_WINDOW", create_no_window, raising=False)
    monkeypatch.setattr(
        tray_app.subprocess, "CREATE_BREAKAWAY_FROM_JOB", create_breakaway, raising=False
    )
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)

    process, used_flags = tray_app._launch_hidden_helper_process(
        ["powershell.exe", "-File", "bootstrap.ps1"],
        on_fallback=notices.append,
    )

    assert process.pid == 9876
    assert calls == [
        create_new_process_group | create_no_window | create_breakaway,
        create_new_process_group | create_no_window,
    ]
    assert used_flags == create_new_process_group | create_no_window
    assert len(notices) == 1
    assert "回退 creationflags=" in notices[0]


def test_schedule_installer_launch_on_windows_silent_uses_hidden_bootstrap_process(
    monkeypatch, tmp_path: Path
) -> None:
    installer_path = tmp_path / "LarkSync-Setup-v0.5.55.exe"
    installer_path.write_bytes(b"exe")
    calls: list[dict[str, object]] = []
    create_new_process_group = 0x200
    create_no_window = 0x08000000
    create_breakaway = 0x01000000

    def _fake_popen(args, **kwargs):
        calls.append({"args": list(args), **kwargs})
        class _DummyProc:
            pid = 1234
        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "win32")
    monkeypatch.setattr(
        tray_app.subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_process_group, raising=False
    )
    monkeypatch.setattr(tray_app.subprocess, "CREATE_NO_WINDOW", create_no_window, raising=False)
    monkeypatch.setattr(
        tray_app.subprocess, "CREATE_BREAKAWAY_FROM_JOB", create_breakaway, raising=False
    )
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(tray_app, "_install_script_dir", lambda: tmp_path / "install-scripts")
    monkeypatch.setattr(
        tray_app,
        "_wait_for_ready_install_handoff",
        lambda *args, **kwargs: {"stage": "helper_started"},
    )

    tray = _build_tray()
    tray._schedule_installer_launch(str(installer_path), silent=True, request_id="req-1")

    assert len(calls) == 1
    assert "-EncodedCommand" not in calls[0]["args"]
    assert "-File" in calls[0]["args"]
    bootstrap_path = Path(calls[0]["args"][calls[0]["args"].index("-File") + 1])
    assert bootstrap_path.is_file()
    assert calls[0]["close_fds"] is True
    creationflags = int(calls[0]["creationflags"])
    assert creationflags & create_new_process_group != 0
    assert creationflags & create_no_window != 0
    assert creationflags & create_breakaway != 0
    assert "workerEncoded" not in bootstrap_path.read_text(encoding="utf-8")
    assert list((tmp_path / "install-scripts").glob("*worker*.ps1"))


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
    monkeypatch.setattr(tray_app, "_install_script_dir", lambda: tmp_path / "install-scripts")
    monkeypatch.setattr(
        tray_app,
        "_wait_for_ready_install_handoff",
        lambda *args, **kwargs: {"stage": "launch_failed", "message": "UAC canceled"},
    )

    tray = _build_tray()

    try:
        tray._schedule_installer_launch(str(installer_path), silent=True, request_id="req-2")
    except RuntimeError as exc:
        assert "UAC canceled" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_schedule_installer_launch_on_windows_silent_rejects_bootstrap_only_handoff(
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
    monkeypatch.setattr(tray_app, "_install_script_dir", lambda: tmp_path / "install-scripts")
    monkeypatch.setattr(
        tray_app,
        "_wait_for_ready_install_handoff",
        lambda *args, **kwargs: {"stage": "bootstrap_started", "message": "worker_pid=1234"},
    )

    tray = _build_tray()

    try:
        tray._schedule_installer_launch(str(installer_path), silent=True, request_id="req-bootstrap")
    except RuntimeError as exc:
        assert "worker 未确认接管" in str(exc)
        assert "worker_pid=1234" in str(exc)
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


def test_install_launch_notice_is_manual_on_macos(monkeypatch) -> None:
    monkeypatch.setattr(tray_app.sys, "platform", "darwin")

    assert "手动重新打开应用" in tray_app._install_launch_notice()


def test_schedule_installer_launch_on_macos_uses_open_command(
    monkeypatch,
    tmp_path: Path,
) -> None:
    installer_path = tmp_path / "LarkSync-v0.6.9.dmg"
    installer_path.write_bytes(b"dmg")
    calls: list[dict[str, object]] = []

    def _fake_popen(args, **kwargs):
        calls.append({"args": list(args), **kwargs})

        class _DummyProc:
            pid = 2468

        return _DummyProc()

    monkeypatch.setattr(tray_app.sys, "platform", "darwin")
    monkeypatch.setattr(tray_app.subprocess, "Popen", _fake_popen)

    tray = _build_tray()
    tray._schedule_installer_launch(str(installer_path))

    assert calls == [
        {
            "args": ["/usr/bin/open", str(installer_path.resolve())],
            "close_fds": True,
        }
    ]
