"""
开机自启动配置 — Windows / macOS 跨平台

Windows: 在 Startup 文件夹创建 .pyw 快捷方式
macOS:   在 ~/Library/LaunchAgents/ 创建 .plist
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LAUNCHER_PYW = _PROJECT_ROOT / "LarkSync.pyw"
_APP_ID = "com.larksync.agent"


def is_autostart_enabled() -> bool:
    """检查是否已配置开机自启动。"""
    if sys.platform == "win32":
        return _win_shortcut_path().is_file()
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
        disable_autostart()
        return False
    else:
        enable_autostart()
        return True


# ---- Windows ----

def _win_shortcut_path() -> Path:
    """获取 Windows Startup 文件夹中的快捷方式路径。"""
    startup = Path(os.environ.get("APPDATA", "")) / (
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    return startup / "LarkSync.lnk"


def _win_enable() -> bool:
    """Windows: 在 Startup 文件夹创建快捷方式。"""
    shortcut_path = _win_shortcut_path()
    target = str(_LAUNCHER_PYW)
    working_dir = str(_PROJECT_ROOT)

    try:
        # 尝试使用 win32com (pywin32)
        import win32com.client  # type: ignore[import-untyped]

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = sys.executable.replace("python.exe", "pythonw.exe")
        shortcut.Arguments = f'"{target}"'
        shortcut.WorkingDirectory = working_dir
        shortcut.Description = "LarkSync 文件同步服务"
        shortcut.save()
        return True
    except ImportError:
        pass

    # Fallback: 使用 PowerShell 创建快捷方式
    import subprocess

    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    ps_cmd = f"""
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut('{shortcut_path}')
    $sc.TargetPath = '{pythonw}'
    $sc.Arguments = '"{target}"'
    $sc.WorkingDirectory = '{working_dir}'
    $sc.Description = 'LarkSync'
    $sc.Save()
    """
    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.returncode == 0


def _win_disable() -> bool:
    """Windows: 删除 Startup 快捷方式。"""
    shortcut = _win_shortcut_path()
    if shortcut.is_file():
        shortcut.unlink()
    return True


# ---- macOS ----

def _mac_plist_path() -> Path:
    """获取 macOS LaunchAgent plist 路径。"""
    return Path.home() / "Library" / "LaunchAgents" / f"{_APP_ID}.plist"


def _mac_enable() -> bool:
    """macOS: 创建 LaunchAgent plist。"""
    plist_path = _mac_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    python_exe = sys.executable
    script = str(_PROJECT_ROOT / "apps" / "tray" / "tray_app.py")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_APP_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{script}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{_PROJECT_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{_PROJECT_ROOT}/data/logs/tray-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{_PROJECT_ROOT}/data/logs/tray-stderr.log</string>
</dict>
</plist>
"""
    plist_path.write_text(plist_content, encoding="utf-8")

    # 加载 plist
    import subprocess
    subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    return True


def _mac_disable() -> bool:
    """macOS: 移除 LaunchAgent。"""
    plist_path = _mac_plist_path()
    if plist_path.is_file():
        import subprocess
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
    return True
