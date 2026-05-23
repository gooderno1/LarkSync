from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import update_install_smoke as smoke


def test_run_update_install_smoke_returns_summary(monkeypatch, tmp_path: Path) -> None:
    handoff = {
        "request_id": "smoke-123",
        "stage": "launch_failed",
        "message": "missing installer",
    }
    launched: list[list[str]] = []
    launch_flags: list[int] = []

    class _DummyProcess:
        pid = 4321

    monkeypatch.setattr(
        smoke.tray_app,
        "_build_windows_silent_bootstrap_command",
        lambda *args, **kwargs: ["powershell.exe", "-File", "bootstrap.ps1"],
    )
    monkeypatch.setattr(
        smoke.tray_app,
        "_launch_hidden_helper_process",
        lambda command, **kwargs: (launched.append(command) or launch_flags.append(0) or _DummyProcess(), 0),
    )
    monkeypatch.setattr(
        smoke,
        "_wait_for_ready_handoff",
        lambda path, request_id, timeout=20.0, expected_stage="launch_failed": handoff,
    )
    monkeypatch.setattr(smoke.sys, "platform", "win32")

    result = smoke.run_update_install_smoke(
        installer_path=tmp_path / "missing-installer.exe",
        expected_stage="launch_failed",
        timeout_seconds=5.0,
    )

    assert launched == [["powershell.exe", "-File", "bootstrap.ps1"]]
    assert launch_flags == [0]
    assert result["success"] is True
    assert result["observed_stage"] == "launch_failed"
    assert result["handoff"] == handoff
    assert result["launch_creationflags"] == 0


def test_run_update_install_smoke_raises_on_unexpected_stage(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        smoke.tray_app,
        "_build_windows_silent_bootstrap_command",
        lambda *args, **kwargs: ["powershell.exe", "-File", "bootstrap.ps1"],
    )
    monkeypatch.setattr(
        smoke.tray_app,
        "_launch_hidden_helper_process",
        lambda *args, **kwargs: (type("_Dummy", (), {"pid": 1})(), 0),
    )
    monkeypatch.setattr(
        smoke,
        "_wait_for_ready_handoff",
        lambda path, request_id, timeout=20.0, expected_stage="launch_failed": {
            "request_id": request_id,
            "stage": "bootstrap_started",
        },
    )
    monkeypatch.setattr(smoke.sys, "platform", "win32")

    try:
        smoke.run_update_install_smoke(
            installer_path=tmp_path / "missing-installer.exe",
            expected_stage="launch_failed",
        )
    except RuntimeError as exc:
        payload = json.loads(str(exc))
        assert payload["expected_stage"] == "launch_failed"
        assert payload["observed_stage"] == "bootstrap_started"
    else:
        raise AssertionError("expected RuntimeError")


def test_run_update_install_smoke_records_fallback_log_when_hidden_launch_denied(
    monkeypatch, tmp_path: Path
) -> None:
    handoff = {
        "request_id": "smoke-123",
        "stage": "launch_failed",
        "message": "missing installer",
    }
    calls: list[int] = []
    breakaway_flag = 0x01000000
    preferred_flags = 0x08000200 | breakaway_flag

    class _DummyProcess:
        pid = 2468

    def _fake_popen(command, creationflags=0, close_fds=True):
        calls.append(int(creationflags))
        if creationflags == preferred_flags:
            raise PermissionError(5, "Access is denied")
        return _DummyProcess()

    monkeypatch.setattr(
        smoke.tray_app,
        "_build_windows_silent_bootstrap_command",
        lambda *args, **kwargs: ["powershell.exe", "-File", "bootstrap.ps1"],
    )
    monkeypatch.setattr(smoke.tray_app.sys, "platform", "win32")
    monkeypatch.setattr(smoke.tray_app.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        smoke.tray_app.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False
    )
    monkeypatch.setattr(smoke.tray_app.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(
        smoke.tray_app.subprocess, "CREATE_BREAKAWAY_FROM_JOB", breakaway_flag, raising=False
    )
    monkeypatch.setattr(
        smoke,
        "_wait_for_ready_handoff",
        lambda path, request_id, timeout=20.0, expected_stage="launch_failed": handoff,
    )
    monkeypatch.setattr(smoke.sys, "platform", "win32")

    result = smoke.run_update_install_smoke(
        installer_path=tmp_path / "missing-installer.exe",
        expected_stage="launch_failed",
        timeout_seconds=5.0,
    )

    log_path = Path(str(result["log_path"]))
    assert calls == [preferred_flags, 0x08000200]
    assert result["launch_creationflags"] == 0x08000200
    assert "回退 creationflags=" in log_path.read_text(encoding="utf-8")
