from __future__ import annotations

import json
import subprocess
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

    class _DummyProcess:
        pid = 4321

    monkeypatch.setattr(
        smoke.tray_app,
        "_build_windows_silent_bootstrap_command",
        lambda *args, **kwargs: ["powershell.exe", "-File", "bootstrap.ps1"],
    )
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda command, creationflags=0: launched.append(command) or _DummyProcess(),
    )
    monkeypatch.setattr(smoke.tray_app, "_hidden_helper_creationflags", lambda: 0)
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
    assert result["success"] is True
    assert result["observed_stage"] == "launch_failed"
    assert result["handoff"] == handoff


def test_run_update_install_smoke_raises_on_unexpected_stage(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        smoke.tray_app,
        "_build_windows_silent_bootstrap_command",
        lambda *args, **kwargs: ["powershell.exe", "-File", "bootstrap.ps1"],
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: type("_Dummy", (), {"pid": 1})())
    monkeypatch.setattr(smoke.tray_app, "_hidden_helper_creationflags", lambda: 0)
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
