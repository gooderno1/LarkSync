import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.tray import autostart


class _CompletedProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_mac_autostart_uses_launcher_script_in_dev_mode(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    python_executable = tmp_path / "venv" / "bin" / "python"
    python_executable.parent.mkdir(parents=True, exist_ok=True)
    python_executable.write_text("", encoding="utf-8")
    launcher_path = repo_root / "apps" / "tray" / "launcher.py"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("print('launcher')\n", encoding="utf-8")
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.larksync.agent.plist"
    runtime_logs = tmp_path / "runtime-logs"
    commands: list[list[str]] = []

    monkeypatch.setattr(autostart.sys, "platform", "darwin")
    monkeypatch.setattr(autostart.sys, "executable", str(python_executable), raising=False)
    monkeypatch.setattr(autostart.sys, "frozen", False, raising=False)
    monkeypatch.setattr(autostart, "_PROJECT_ROOT", repo_root)
    monkeypatch.setattr(autostart, "_mac_plist_path", lambda: plist_path)
    monkeypatch.setattr(autostart, "logs_dir", lambda: runtime_logs)
    monkeypatch.setattr(
        autostart.subprocess,
        "run",
        lambda cmd, **kwargs: commands.append(cmd) or _CompletedProcess(),
    )

    assert autostart.enable_autostart() is True

    content = plist_path.read_text(encoding="utf-8")
    assert f"<string>{python_executable}</string>" in content
    assert f"<string>{launcher_path}</string>" in content
    assert str(runtime_logs / "tray-stdout.log") in content
    assert str(runtime_logs / "tray-stderr.log") in content
    assert commands == [["launchctl", "load", str(plist_path)]]


def test_mac_autostart_uses_bundled_executable_when_frozen(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.larksync.agent.plist"
    runtime_logs = tmp_path / "runtime-logs"
    executable = tmp_path / "Applications" / "LarkSync.app" / "Contents" / "MacOS" / "LarkSync"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(autostart.sys, "platform", "darwin")
    monkeypatch.setattr(autostart.sys, "executable", str(executable), raising=False)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart, "_PROJECT_ROOT", repo_root)
    monkeypatch.setattr(autostart, "_mac_plist_path", lambda: plist_path)
    monkeypatch.setattr(autostart, "logs_dir", lambda: runtime_logs)
    monkeypatch.setattr(
        autostart.subprocess,
        "run",
        lambda cmd, **kwargs: commands.append(cmd) or _CompletedProcess(),
    )

    assert autostart.enable_autostart() is True

    content = plist_path.read_text(encoding="utf-8")
    assert f"<string>{executable}</string>" in content
    assert "launcher.py" not in content
    assert commands == [["launchctl", "load", str(plist_path)]]
