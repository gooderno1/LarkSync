import sys
import types
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


class _FakeShortcut:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.Targetpath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.Description = ""

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("shortcut", encoding="utf-8")


class _FakeShell:
    def __init__(self) -> None:
        self.shortcuts: dict[str, _FakeShortcut] = {}

    def CreateShortCut(self, path: str) -> _FakeShortcut:
        if path not in self.shortcuts:
            self.shortcuts[path] = _FakeShortcut(path)
        return self.shortcuts[path]


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


def test_win_autostart_uses_tracked_launcher_in_dev_mode(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    python_executable = tmp_path / "venv" / "Scripts" / "python.exe"
    pythonw_executable = python_executable.with_name("pythonw.exe")
    launcher_path = repo_root / "apps" / "tray" / "launcher.py"
    appdata = tmp_path / "AppData" / "Roaming"
    shortcut_path = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "LarkSync.lnk"
    fake_shell = _FakeShell()
    python_executable.parent.mkdir(parents=True, exist_ok=True)
    python_executable.write_text("", encoding="utf-8")
    pythonw_executable.write_text("", encoding="utf-8")
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("print('launcher')\n", encoding="utf-8")

    fake_win32com = types.ModuleType("win32com")
    fake_win32com_client = types.ModuleType("win32com.client")
    fake_win32com_client.Dispatch = lambda name: fake_shell
    fake_win32com.client = fake_win32com_client  # type: ignore[attr-defined]

    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setattr(autostart.sys, "executable", str(python_executable), raising=False)
    monkeypatch.setattr(autostart.sys, "frozen", False, raising=False)
    monkeypatch.setattr(autostart, "_PROJECT_ROOT", repo_root)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setitem(sys.modules, "win32com", fake_win32com)
    monkeypatch.setitem(sys.modules, "win32com.client", fake_win32com_client)

    assert autostart.enable_autostart() is True
    shortcut = fake_shell.shortcuts[str(shortcut_path)]
    assert shortcut.Targetpath == str(pythonw_executable)
    assert shortcut.Arguments == f'"{launcher_path}"'
    assert shortcut.WorkingDirectory == str(repo_root)
    assert autostart.is_autostart_enabled() is True


def test_win_autostart_uses_bundled_executable_when_frozen(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    executable = tmp_path / "Program Files" / "LarkSync" / "LarkSync.exe"
    appdata = tmp_path / "AppData" / "Roaming"
    shortcut_path = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "LarkSync.lnk"
    fake_shell = _FakeShell()
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("", encoding="utf-8")

    fake_win32com = types.ModuleType("win32com")
    fake_win32com_client = types.ModuleType("win32com.client")
    fake_win32com_client.Dispatch = lambda name: fake_shell
    fake_win32com.client = fake_win32com_client  # type: ignore[attr-defined]

    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setattr(autostart.sys, "executable", str(executable), raising=False)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart, "_PROJECT_ROOT", repo_root)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setitem(sys.modules, "win32com", fake_win32com)
    monkeypatch.setitem(sys.modules, "win32com.client", fake_win32com_client)

    assert autostart.enable_autostart() is True
    shortcut = fake_shell.shortcuts[str(shortcut_path)]
    assert shortcut.Targetpath == str(executable)
    assert shortcut.Arguments == ""
    assert shortcut.WorkingDirectory == str(executable.parent)


def test_toggle_autostart_returns_false_when_enable_fails(monkeypatch) -> None:
    monkeypatch.setattr(autostart, "is_autostart_enabled", lambda: False)
    monkeypatch.setattr(autostart, "enable_autostart", lambda: False)

    assert autostart.toggle_autostart() is False
