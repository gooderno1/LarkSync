"""
开机自启动配置 — Windows / macOS 跨平台

Windows: 在 Startup 文件夹创建 .pyw 快捷方式
macOS:   在 ~/Library/LaunchAgents/ 创建 .plist
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _PROJECT_ROOT / "apps" / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_APP_ID = "com.larksync.agent"

from src.core.paths import logs_dir


def is_autostart_enabled() -> bool:
    """检查是否已配置开机自启动。"""
    if sys.platform == "win32":
        return _win_is_enabled()
    elif sys.platform == "darwin":
        return _mac_plist_path().is_file()
    return False


def enable_autostart() -> bool:
    """启用开机自启动。"""
    try:
        if sys.platform == "win32":
            return _win_enable()
        elif sys.platform == "darwin":
            return _mac_enable()
        else:
            print(f"不支持的平台: {sys.platform}")
            return False
    except Exception as exc:
        print(f"启用自启动失败: {exc}")
        return False


def disable_autostart() -> bool:
    """禁用开机自启动。"""
    try:
        if sys.platform == "win32":
            return _win_disable()
        elif sys.platform == "darwin":
            return _mac_disable()
        else:
            return False
    except Exception as exc:
        print(f"禁用自启动失败: {exc}")
        return False


def toggle_autostart() -> bool:
    """切换自启动状态，返回新状态。"""
    if is_autostart_enabled():
        return not disable_autostart()
    return enable_autostart()


def repair_autostart_if_needed() -> bool:
    """修复已存在但已过时的自启动配置。"""
    if sys.platform != "win32":
        return False
    shortcut = _win_shortcut_path()
    if not shortcut.is_file():
        return False
    if _win_shortcut_matches_expected():
        return False
    return _win_enable()


# ---- Windows ----

def _win_shortcut_path() -> Path:
    """获取 Windows Startup 文件夹中的快捷方式路径。"""
    startup = Path(os.environ.get("APPDATA", "")) / (
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    return startup / "LarkSync.lnk"


def _legacy_launcher_path() -> Path:
    return _PROJECT_ROOT / "LarkSync.pyw"


def _tracked_launcher_path() -> Path:
    return _PROJECT_ROOT / "apps" / "tray" / "launcher.py"


def _resolve_tray_entry_script() -> Path:
    tracked = _tracked_launcher_path()
    if tracked.is_file():
        return tracked.resolve()

    legacy = _legacy_launcher_path()
    if legacy.is_file():
        return legacy.resolve()

    raise FileNotFoundError(f"未找到托盘入口脚本：{tracked} 或 {legacy}")


def _powershell_quote(value: str) -> str:
    return value.replace("'", "''")


def _win_resolve_powershell_executable() -> str:
    system_root = os.getenv("SystemRoot", r"C:\Windows")
    candidates = [
        Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        Path(system_root) / "Sysnative" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return "powershell"


def _win_shortcut_target() -> str:
    executable = Path(sys.executable).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return str(executable)
    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.is_file():
            return str(pythonw)
    return str(executable)


def _win_shortcut_arguments() -> str:
    if getattr(sys, "frozen", False):
        return ""
    return f'"{_resolve_tray_entry_script()}"'


def _win_shortcut_working_directory() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).expanduser().resolve().parent)
    return str(_PROJECT_ROOT.resolve())


def _normalize_win_path(value: str) -> str:
    cleaned = (value or "").strip().strip('"')
    if not cleaned:
        return ""
    return str(Path(cleaned).expanduser().resolve())


def _win_shortcut_spec() -> dict[str, str]:
    return {
        "target": _win_shortcut_target(),
        "arguments": _win_shortcut_arguments(),
        "working_directory": _win_shortcut_working_directory(),
    }


def _win_read_shortcut_spec() -> dict[str, str] | None:
    shortcut_path = _win_shortcut_path()
    if not shortcut_path.is_file():
        return None

    try:
        import win32com.client  # type: ignore[import-untyped]

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        return {
            "target": str(getattr(shortcut, "Targetpath", "") or ""),
            "arguments": str(getattr(shortcut, "Arguments", "") or ""),
            "working_directory": str(getattr(shortcut, "WorkingDirectory", "") or ""),
        }
    except ImportError:
        pass

    ps_cmd = f"""
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut('{_powershell_quote(str(shortcut_path))}')
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [PSCustomObject]@{{
        target = $sc.TargetPath
        arguments = $sc.Arguments
        working_directory = $sc.WorkingDirectory
    }} | ConvertTo-Json -Compress
    """
    result = subprocess.run(
        [_win_resolve_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads((result.stdout or "").strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "target": str(payload.get("target", "") or ""),
        "arguments": str(payload.get("arguments", "") or ""),
        "working_directory": str(payload.get("working_directory", "") or ""),
    }


def _win_shortcut_matches_expected() -> bool:
    shortcut_path = _win_shortcut_path()
    if not shortcut_path.is_file():
        return False

    actual = _win_read_shortcut_spec()
    if actual is None:
        return True

    expected = _win_shortcut_spec()
    return (
        _normalize_win_path(actual["target"]) == _normalize_win_path(expected["target"])
        and (actual["arguments"] or "").strip() == expected["arguments"]
        and _normalize_win_path(actual["working_directory"])
        == _normalize_win_path(expected["working_directory"])
    )


def _win_is_enabled() -> bool:
    shortcut_path = _win_shortcut_path()
    if not shortcut_path.is_file():
        return False
    return _win_shortcut_matches_expected()


def _win_enable() -> bool:
    """Windows: 在 Startup 文件夹创建快捷方式。"""
    shortcut_path = _win_shortcut_path()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    spec = _win_shortcut_spec()

    try:
        # 尝试使用 win32com (pywin32)
        import win32com.client  # type: ignore[import-untyped]

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = spec["target"]
        shortcut.Arguments = spec["arguments"]
        shortcut.WorkingDirectory = spec["working_directory"]
        shortcut.Description = "LarkSync 文件同步服务"
        shortcut.save()
        return True
    except ImportError:
        pass

    # Fallback: 使用 PowerShell 创建快捷方式
    ps_cmd = f"""
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut('{_powershell_quote(str(shortcut_path))}')
    $sc.TargetPath = '{_powershell_quote(spec["target"])}'
    $sc.Arguments = '{_powershell_quote(spec["arguments"])}'
    $sc.WorkingDirectory = '{_powershell_quote(spec["working_directory"])}'
    $sc.Description = 'LarkSync'
    $sc.Save()
    """
    result = subprocess.run(
        [_win_resolve_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def _win_disable() -> bool:
    """Windows: 删除 Startup 快捷方式。"""
    shortcut = _win_shortcut_path()
    if shortcut.is_file():
        shortcut.unlink()
    return True


# ---- macOS ----

def _mac_launcher_script() -> Path:
    launcher = _PROJECT_ROOT / "apps" / "tray" / "launcher.py"
    if launcher.is_file():
        return launcher
    return _PROJECT_ROOT / "apps" / "tray" / "tray_app.py"


def _mac_program_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).expanduser().resolve())]
    return [
        str(Path(sys.executable).expanduser().resolve()),
        str(_mac_launcher_script()),
    ]


def _mac_working_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).expanduser().resolve().parent
    return _PROJECT_ROOT


def _plist_string(value: str) -> str:
    return f"<string>{escape(value, quote=True)}</string>"


def _mac_plist_path() -> Path:
    """获取 macOS LaunchAgent plist 路径。"""
    return Path.home() / "Library" / "LaunchAgents" / f"{_APP_ID}.plist"


def _mac_enable() -> bool:
    """macOS: 创建 LaunchAgent plist。"""
    plist_path = _mac_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir = logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    program_args_xml = "\n".join(
        f"        {_plist_string(arg)}" for arg in _mac_program_arguments()
    )

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    {_plist_string(_APP_ID)}
    <key>ProgramArguments</key>
    <array>
{program_args_xml}
    </array>
    <key>WorkingDirectory</key>
    {_plist_string(str(_mac_working_directory()))}
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    {_plist_string(str(log_dir / "tray-stdout.log"))}
    <key>StandardErrorPath</key>
    {_plist_string(str(log_dir / "tray-stderr.log"))}
</dict>
</plist>
"""
    plist_path.write_text(plist_content, encoding="utf-8")

    subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    return True


def _mac_disable() -> bool:
    """macOS: 移除 LaunchAgent。"""
    plist_path = _mac_plist_path()
    if plist_path.is_file():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
    return True
