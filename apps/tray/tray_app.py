"""
LarkSync 系统托盘应用 — 主入口

功能：
- 启动/管理后端 FastAPI 服务
- 系统托盘图标（状态可视化）
- 右键菜单（打开面板/暂停/日志/退出）
- 状态轮询 + 图标动态切换
- 系统通知（冲突/错误）
- --dev 模式：同时启动 Vite 前端热重载 + uvicorn --reload
"""

from __future__ import annotations

import atexit
import base64
import sys
import os
import re
import signal
import socket
import subprocess
import threading
import time
import webbrowser
import json
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import Any

# 确保项目根目录在 sys.path 中
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
_BACKEND_ROOT = os.path.join(_PROJECT_ROOT, "apps", "backend")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from apps.tray.config import (
    BACKEND_HOST,
    BACKEND_URL,
    STATUS_POLL_INTERVAL,
    TRAY_STATUS_URL,
    FRONTEND_DIR,
    VITE_DEV_PORT,
    VITE_DEV_URL,
    get_dashboard_url,
    get_settings_url,
    get_logs_url,
    _is_port_active,
)
from apps.tray.backend_manager import BackendManager
from apps.tray.icon_generator import generate_icons, get_icon_path
from apps.tray.autostart import is_autostart_enabled, toggle_autostart
from apps.tray import notifier
from src.core.paths import update_data_dir, update_logs_dir


def _sanitize_runtime_pythonpath() -> None:
    """清理与当前解释器版本不兼容的 PYTHONPATH/site-packages，避免托盘依赖导入失败。"""
    raw_pythonpath = os.getenv("PYTHONPATH")
    if not raw_pythonpath:
        return

    current_tag = f"{sys.version_info.major}{sys.version_info.minor}"

    def _is_mismatched_site_packages(entry: str) -> bool:
        normalized = entry.replace("\\", "/").lower()
        version_tags = re.findall(r"python(\d{2,3})", normalized)
        has_mismatch = bool(version_tags) and any(tag != current_tag for tag in version_tags)
        return has_mismatch and "site-packages" in normalized

    env_entries = [part.strip() for part in raw_pythonpath.split(os.pathsep) if part.strip()]
    kept_env_entries = [part for part in env_entries if not _is_mismatched_site_packages(part)]
    if kept_env_entries != env_entries:
        if kept_env_entries:
            os.environ["PYTHONPATH"] = os.pathsep.join(kept_env_entries)
        else:
            os.environ.pop("PYTHONPATH", None)
        print("警告：检测到不兼容 PYTHONPATH，已为托盘进程自动过滤。")

    cleaned_sys_path: list[str] = []
    for entry in sys.path:
        if not isinstance(entry, str) or not entry.strip():
            cleaned_sys_path.append(entry)
            continue
        if _is_mismatched_site_packages(entry):
            continue
        cleaned_sys_path.append(entry)
    sys.path[:] = cleaned_sys_path


_sanitize_runtime_pythonpath()

# ---- 延迟导入 pystray / PIL（可能未安装） ----
_TRAY_IMPORT_ERROR: str | None = None
try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except Exception as exc:
    _TRAY_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    HAS_TRAY = False


_LOCK_SOCKET: socket.socket | None = None
_INSTALL_REQUEST_MIN_AGE_SECONDS = 2.0
_INSTALL_HANDOFF_TIMEOUT_SECONDS = 15.0


def _data_dir() -> Path:
    env_dir = os.getenv("LARKSYNC_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    root = Path(_PROJECT_ROOT)
    if (root / "apps").exists() and (root / "data").exists():
        return root / "data"
    if sys.platform == "win32":
        base = os.getenv("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "LarkSync"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LarkSync"
    base = os.getenv("XDG_DATA_HOME")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "LarkSync"


def _install_request_path() -> Path:
    return update_data_dir() / "install-request.json"


def _install_handoff_path() -> Path:
    return update_data_dir() / "install-handoff.json"


def _load_install_request() -> dict[str, str | float | bool] | None:
    path = _install_request_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    installer_path = str(payload.get("installer_path", "")).strip()
    if not installer_path:
        return None
    created_at_raw = payload.get("created_at")
    try:
        created_at = float(created_at_raw) if created_at_raw is not None else 0.0
    except (TypeError, ValueError):
        created_at = 0.0
    silent = bool(payload.get("silent", False))
    restart_path = str(payload.get("restart_path", "")).strip()
    return {
        "request_id": str(payload.get("request_id", "")).strip(),
        "installer_path": installer_path,
        "created_at": created_at,
        "silent": silent,
        "restart_path": restart_path,
    }


def _clear_install_request() -> None:
    _install_request_path().unlink(missing_ok=True)


def _clear_install_handoff() -> None:
    _install_handoff_path().unlink(missing_ok=True)


def _append_install_launch_log(message: str) -> None:
    try:
        log_path = update_logs_dir() / "update-install.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with log_path.open("a", encoding="utf-8", errors="ignore") as file:
            file.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def _read_install_handoff() -> dict[str, Any] | None:
    path = _install_handoff_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _wait_for_install_handoff(
    request_id: str,
    *,
    timeout: float = _INSTALL_HANDOFF_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    if not request_id:
        return None
    deadline = time.time() + max(timeout, 0.1)
    while time.time() < deadline:
        payload = _read_install_handoff()
        if payload and str(payload.get("request_id", "")).strip() == request_id:
            return payload
        time.sleep(0.2)
    return None


def _resolve_powershell_executable() -> str:
    if sys.platform != "win32":
        return "powershell"
    system_root = os.getenv("SystemRoot", r"C:\Windows")
    candidates = [
        Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        Path(system_root) / "Sysnative" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return "powershell"


def _build_windows_installer_launch_command(
    path: Path,
    *,
    silent: bool = False,
    restart_path: Path | None = None,
    log_path: Path | None = None,
    handoff_path: Path | None = None,
    request_id: str = "",
) -> list[str]:
    installer_escaped = str(path).replace("'", "''")
    restart_escaped = str(restart_path).replace("'", "''") if restart_path else ""
    log_escaped = str(log_path).replace("'", "''") if log_path else ""
    handoff_escaped = str(handoff_path).replace("'", "''") if handoff_path else ""
    request_escaped = request_id.replace("'", "''")
    silent_literal = "$true" if silent else "$false"
    script = (
        f"$installerPath = '{installer_escaped}'; "
        f"$restartPath = '{restart_escaped}'; "
        f"$logPath = '{log_escaped}'; "
        f"$handoffPath = '{handoff_escaped}'; "
        f"$requestId = '{request_escaped}'; "
        f"$silentInstall = {silent_literal}; "
        "function Write-InstallLog([string]$message) { "
        "if ([string]::IsNullOrWhiteSpace($logPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $logPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'; "
        "Add-Content -LiteralPath $logPath -Value \"[$timestamp] $message\" -Encoding UTF8 "
        "} catch {} "
        "}; "
        "function Write-Handoff([string]$stage, [string]$message, [int]$exitCode = 0) { "
        "if ([string]::IsNullOrWhiteSpace($handoffPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $handoffPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$payload = @{ request_id = $requestId; stage = $stage; message = $message; exit_code = $exitCode; timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() } | ConvertTo-Json -Compress; "
        "Set-Content -LiteralPath $handoffPath -Value $payload -Encoding UTF8 "
        "} catch {} "
        "}; "
        "Write-Handoff 'helper_started' 'helper process started'; "
        "$argumentList = @(); "
        "if ($silentInstall) { $argumentList += '/S' }; "
        "Write-InstallLog (\"启动安装器请求: installer=\" + $installerPath + \" silent=\" + $silentInstall); "
        "try { "
        "$process = Start-Process -FilePath $installerPath -ArgumentList $argumentList -PassThru -ErrorAction Stop; "
        "} catch { "
        "$message = $_.Exception.Message; "
        "Write-Handoff 'launch_failed' $message 0; "
        "Write-InstallLog (\"启动安装器失败: \" + $message); "
        "if (-not [string]::IsNullOrWhiteSpace($restartPath)) { Start-Process -FilePath $restartPath; Write-InstallLog (\"安装器未启动，已恢复当前版本: \" + $restartPath) }; "
        "exit 1 "
        "}; "
        "Write-Handoff 'installer_started' ('pid=' + $process.Id) 0; "
        "Write-InstallLog (\"安装器进程已启动 pid=\" + $process.Id); "
        "Wait-Process -Id $process.Id; "
        "$process.Refresh(); "
        "$exitCode = $process.ExitCode; "
        "Write-InstallLog (\"安装器进程已退出 exit_code=\" + $exitCode); "
        "if ($exitCode -ne 0) { "
        "Write-Handoff 'install_failed' ('exit_code=' + $exitCode) $exitCode; "
        "if (-not [string]::IsNullOrWhiteSpace($restartPath)) { Start-Process -FilePath $restartPath; Write-InstallLog (\"安装失败，已恢复当前版本: \" + $restartPath) }; "
        "exit $exitCode "
        "}; "
        "Write-Handoff 'install_succeeded' 'installer completed successfully' $exitCode; "
        "if (-not [string]::IsNullOrWhiteSpace($restartPath)) { "
        "Start-Sleep -Milliseconds 1200; "
        "Start-Process -FilePath $restartPath; "
        "Write-InstallLog (\"已请求重启新版本: \" + $restartPath) "
        "}"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [
        _resolve_powershell_executable(),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-EncodedCommand",
        encoded,
    ]


def _startfile_windows_installer(path: Path) -> bool:
    launcher = getattr(os, "startfile", None)
    if launcher is None:
        return False
    launcher(str(path))
    return True


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """等待端口变为可用，返回是否成功。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_port_active(port):
            return True
        time.sleep(0.3)
    return False


def _truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _kill_process_tree(pid: int) -> None:
    """终止进程及其所有子进程（Windows 使用 taskkill /T，其他平台使用 SIGTERM）。"""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
            )
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        pass


class LarkSyncTray:
    """LarkSync 系统托盘应用。"""

    def __init__(self, dev_mode: bool = False) -> None:
        self._dev_mode = dev_mode
        self._backend = BackendManager(dev_mode=dev_mode)
        self._vite_process: subprocess.Popen | None = None
        self._icon: pystray.Icon | None = None
        self._current_state = "idle"
        self._global_paused = False
        self._poller_thread: threading.Thread | None = None
        self._running = False
        self._last_conflict_count: int = 0

        # 确保图标已生成
        generate_icons()

    # ---- 公共方法 ----

    def run(self) -> None:
        """启动托盘应用（阻塞式）。"""
        if not HAS_TRAY:
            print("错误：未检测到托盘依赖（pystray / Pillow），无法显示系统托盘图标。")
            if _TRAY_IMPORT_ERROR:
                print(f"导入详情：{_TRAY_IMPORT_ERROR}")
            print("请先安装依赖：")
            print("  python -m pip install -r apps/backend/requirements.txt")
            if self._dev_mode and _truthy_env(os.getenv("LARKSYNC_ALLOW_HEADLESS_DEV")):
                print("检测到 LARKSYNC_ALLOW_HEADLESS_DEV=1，进入无托盘开发模式。")
                self._run_headless_dev_mode()
                return
            sys.exit(1)

        self._running = True

        # 注册 atexit 确保无论如何退出都清理子进程
        atexit.register(self._cleanup_all)

        # dev 模式：先启动 Vite 前端开发服务器
        if self._dev_mode:
            self._start_vite()

        # 启动后端
        mode_label = "开发" if self._dev_mode else "生产"
        print(f"正在启动 LarkSync 后端（{mode_label}模式）...")
        success = self._backend.start(wait=True)

        if success:
            # dev 模式：等待 Vite 端口就绪后再打开浏览器
            if self._dev_mode:
                print("等待 Vite 前端就绪...")
                if _wait_for_port(VITE_DEV_PORT, timeout=15):
                    dashboard = f"{VITE_DEV_URL}/"
                    print(f"Vite 就绪，打开管理面板: {dashboard}")
                else:
                    print("警告：Vite 启动超时，尝试打开 3666...")
                    dashboard = f"{VITE_DEV_URL}/"
            else:
                dashboard = get_dashboard_url()
                print(f"后端已就绪，打开管理面板: {dashboard}")
            webbrowser.open(dashboard)
            self._notify(
                "LarkSync 已启动",
                "托盘图标已启动；若未看到，请在任务栏隐藏图标中查找。",
                category="startup",
            )
        else:
            print("警告：后端启动失败，请检查日志。")

        # 启动状态轮询线程
        self._poller_thread = threading.Thread(
            target=self._poll_status_loop,
            daemon=True,
            name="status-poller",
        )
        self._poller_thread.start()

        # 创建托盘图标（此调用会阻塞）
        # 使用 try/finally 确保退出时清理
        self._icon = pystray.Icon(
            name="LarkSync",
            icon=self._load_icon("idle"),
            title="LarkSync — 同步服务",
            menu=self._build_menu(),
        )
        try:
            self._icon.run()
        finally:
            # pystray.run() 退出后（无论是正常退出还是异常），清理所有子进程
            self._cleanup_all()

    def _run_headless_dev_mode(self) -> None:
        """缺少托盘依赖时的开发模式降级入口。"""
        self._running = True
        atexit.register(self._cleanup_all)
        self._start_vite()
        print("正在启动后端服务（无托盘模式）...")
        success = self._backend.start(wait=True)
        if success:
            print(f"后端就绪，打开管理面板: {VITE_DEV_URL}/")
            webbrowser.open(f"{VITE_DEV_URL}/")
        else:
            print("警告：后端启动失败，请检查日志。")
        try:
            while self._running:
                if self._handle_pending_install_request():
                    break
                self._backend.maybe_auto_restart()
                time.sleep(STATUS_POLL_INTERVAL)
        finally:
            self._cleanup_all()

    def stop(self) -> None:
        """退出托盘应用，关闭所有子进程。"""
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _cleanup_all(self) -> None:
        """清理所有子进程（Vite + 后端）。确保在任何退出场景下都被调用。"""
        self._running = False
        self._stop_vite()
        self._backend.stop()

    # ---- Vite 前端开发服务器管理 ----

    def _start_vite(self) -> None:
        """启动 Vite 前端开发服务器（仅 dev 模式）。"""
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_dir = str(FRONTEND_DIR)

        print("正在启动 Vite 前端开发服务器（端口 3666）...")

        # 日志文件
        log_dir = os.path.join(_PROJECT_ROOT, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        vite_log_path = os.path.join(log_dir, "vite-dev.log")
        vite_log = open(vite_log_path, "a", encoding="utf-8")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            self._vite_process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=frontend_dir,
                creationflags=creationflags,
                stdout=vite_log,
                stderr=vite_log,
            )
            print(f"Vite 已启动 (PID {self._vite_process.pid})，日志: {vite_log_path}")
        except Exception as exc:
            print(f"警告：Vite 启动失败: {exc}")
            self._vite_process = None

    def _stop_vite(self) -> None:
        """停止 Vite 前端开发服务器。"""
        if not self._vite_process:
            return
        pid = self._vite_process.pid
        _kill_process_tree(pid)
        try:
            self._vite_process.wait(timeout=5)
        except Exception:
            pass
        self._vite_process = None
        print("Vite 前端开发服务器已停止")

    # ---- 菜单构建 ----

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                self._status_text,
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "打开管理面板",
                self._on_open_dashboard,
                default=True,  # 双击图标的默认动作
            ),
            pystray.MenuItem(
                "立即同步",
                self._on_sync_now,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: "恢复同步" if self._global_paused else "暂停同步",
                self._on_toggle_pause,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("设置", self._on_open_settings),
            pystray.MenuItem("查看日志", self._on_open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: "✓ 开机自启动" if is_autostart_enabled() else "  开机自启动",
                self._on_toggle_autostart,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出 LarkSync", self._on_quit),
        )

    def _status_text(self, _item=None) -> str:
        """动态生成状态文字。"""
        state_labels = {
            "idle": "运行中 — 空闲",
            "syncing": "同步中...",
            "error": "有错误需要处理",
            "paused": "已暂停",
        }
        return f"LarkSync — {state_labels.get(self._current_state, '未知')}"

    # ---- 菜单回调 ----

    def _get_frontend_url(self) -> str:
        """获取当前前端 URL。dev 模式固定返回 3666。"""
        if self._dev_mode:
            return VITE_DEV_URL
        return get_dashboard_url().rstrip("/")

    def _on_open_dashboard(self, icon=None, item=None) -> None:
        webbrowser.open(f"{self._get_frontend_url()}/")

    def _on_open_settings(self, icon=None, item=None) -> None:
        webbrowser.open(f"{self._get_frontend_url()}/#settings")

    def _on_open_logs(self, icon=None, item=None) -> None:
        webbrowser.open(f"{self._get_frontend_url()}/#logcenter")

    def _on_sync_now(self, icon=None, item=None) -> None:
        """触发所有启用任务立即运行。"""
        try:
            # 获取任务列表
            req = urllib.request.Request(f"{BACKEND_URL}/sync/tasks")
            with urllib.request.urlopen(req, timeout=5) as resp:
                tasks = json.loads(resp.read())
            # 逐个触发
            for task in tasks:
                if task.get("enabled"):
                    run_req = urllib.request.Request(
                        f"{BACKEND_URL}/sync/tasks/{task['id']}/run",
                        method="POST",
                        data=b"",
                    )
                    urllib.request.urlopen(run_req, timeout=10)
        except Exception:
            pass  # 静默失败，状态轮询会反映实际情况

    def _on_toggle_pause(self, icon=None, item=None) -> None:
        """切换全局暂停/恢复。"""
        self._global_paused = not self._global_paused
        if self._global_paused:
            self._set_state("paused")
        else:
            self._set_state("idle")
        # 更新菜单
        if self._icon:
            self._icon.update_menu()

    def _on_toggle_autostart(self, icon=None, item=None) -> None:
        """切换开机自启动。"""
        new_state = toggle_autostart()
        state_text = "已启用" if new_state else "已禁用"
        self._notify(f"开机自启动{state_text}", f"LarkSync 开机自启动已{state_text}。")
        if self._icon:
            self._icon.update_menu()

    def _on_quit(self, icon=None, item=None) -> None:
        """退出应用。"""
        self.stop()

    def _handle_pending_install_request(self) -> bool:
        request = _load_install_request()
        if not request:
            return False
        request_id = str(request.get("request_id") or "").strip()
        installer_path = request["installer_path"]
        silent = bool(request.get("silent", False))
        restart_path = str(request.get("restart_path") or "").strip() or None
        created_at = float(request.get("created_at") or 0.0)
        if created_at > 0 and (time.time() - created_at) < _INSTALL_REQUEST_MIN_AGE_SECONDS:
            return False
        try:
            _clear_install_handoff()
            _append_install_launch_log(
                f"准备启动安装包: {installer_path} (silent={silent} restart={restart_path or '-'})"
            )
            self._schedule_installer_launch(
                installer_path,
                silent=silent,
                restart_path=restart_path,
                request_id=request_id,
            )
        except Exception as exc:
            _append_install_launch_log(f"启动安装包失败: {installer_path} ({type(exc).__name__}: {exc})")
            print(f"警告：启动安装程序失败: {exc}")
            _clear_install_request()
            self._notify(
                "更新安装启动失败",
                "安装程序未能成功接管，本次更新已取消，请重新下载后再试。",
                category="update",
            )
            return False
        _clear_install_request()
        _append_install_launch_log(f"已调度安装包启动: {installer_path}")
        self._notify(
            "正在启动更新安装",
            "LarkSync 将退出并执行更新安装，完成后会自动重新启动。",
            category="update",
        )
        self.stop()
        return True

    def _schedule_installer_launch(
        self,
        installer_path: str,
        *,
        silent: bool = False,
        restart_path: str | None = None,
        request_id: str = "",
    ) -> None:
        path = Path(installer_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"安装包不存在: {path}")
        restart_target: Path | None = None
        if restart_path:
            restart_target = Path(restart_path).expanduser().resolve()
            if not restart_target.is_file():
                raise FileNotFoundError(f"重启程序不存在: {restart_target}")

        if sys.platform == "win32":
            if silent:
                creationflags = (
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                subprocess.Popen(
                    _build_windows_installer_launch_command(
                        path,
                        silent=True,
                        restart_path=restart_target,
                        log_path=update_logs_dir() / "update-install.log",
                        handoff_path=_install_handoff_path(),
                        request_id=request_id,
                    ),
                    creationflags=creationflags,
                    close_fds=True,
                )
                handoff = _wait_for_install_handoff(request_id)
                if not handoff:
                    raise RuntimeError("静默安装接管超时，安装程序未返回接管确认")
                stage = str(handoff.get("stage") or "").strip()
                if stage == "helper_started" or stage == "installer_started":
                    return
                message = str(handoff.get("message") or "").strip() or "静默安装接管失败"
                raise RuntimeError(message)
                return
            try:
                if _startfile_windows_installer(path):
                    _append_install_launch_log(f"已请求 ShellExecute 启动安装包: {path}")
                    return
            except OSError as exc:
                _append_install_launch_log(
                    f"ShellExecute 启动失败，回退 PowerShell: {path} ({type(exc).__name__}: {exc})"
                )
            creationflags = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            subprocess.Popen(
                _build_windows_installer_launch_command(
                    path,
                    restart_path=restart_target,
                    log_path=update_logs_dir() / "update-install.log",
                ),
                creationflags=creationflags,
                close_fds=True,
            )
            return

        if sys.platform == "darwin":
            subprocess.Popen(["/usr/bin/open", str(path)], close_fds=True)
            return

        opener = "xdg-open"
        subprocess.Popen([opener, str(path)], close_fds=True)

    # ---- 状态轮询 ----

    def _poll_status_loop(self) -> None:
        """后台线程：定期查询后端状态并更新图标。"""
        while self._running:
            try:
                if self._handle_pending_install_request():
                    return
                # 检查后端是否需要重启
                needs_notify = self._backend.maybe_auto_restart()
                if needs_notify:
                    self._set_state("error")
                    notifier.notify_backend_crash()
                    time.sleep(STATUS_POLL_INTERVAL)
                    continue

                if self._global_paused:
                    time.sleep(STATUS_POLL_INTERVAL)
                    continue

                # 查询聚合状态
                status = self._fetch_tray_status()
                if status is None:
                    self._set_state("error")
                else:
                    conflicts = int(status.get("unresolved_conflicts", 0) or 0)
                    if conflicts > 0:
                        if conflicts > self._last_conflict_count:
                            self._notify(
                                "检测到未解决的同步冲突",
                                f"当前有 {conflicts} 个冲突，请在管理面板处理。",
                                category="conflict",
                            )
                        self._last_conflict_count = conflicts
                        self._set_state("error")
                        time.sleep(STATUS_POLL_INTERVAL)
                        continue
                    self._last_conflict_count = 0

                    if status.get("tasks_running", 0) > 0:
                        self._set_state("syncing")
                    elif status.get("last_error"):
                        self._set_state("error")
                    else:
                        self._set_state("idle")

            except Exception:
                pass  # 轮询异常不应中断

            time.sleep(STATUS_POLL_INTERVAL)

    def _fetch_tray_status(self) -> dict | None:
        """获取后端 /tray/status 接口数据。"""
        try:
            req = urllib.request.Request(TRAY_STATUS_URL)
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    # ---- 图标与通知 ----

    def _set_state(self, state: str) -> None:
        """更新托盘图标状态。"""
        if state == self._current_state:
            return
        self._current_state = state
        if self._icon:
            self._icon.icon = self._load_icon(state)
            self._icon.title = self._status_text()

    def _load_icon(self, state: str) -> "Image.Image":
        """加载指定状态的图标。"""
        icon_path = get_icon_path(state)
        if icon_path and icon_path.is_file():
            return Image.open(str(icon_path))
        # fallback: 生成一个简单的彩色方块
        colors = {
            "idle": (16, 185, 129),
            "syncing": (51, 112, 255),
            "error": (244, 63, 94),
            "paused": (113, 113, 122),
        }
        color = colors.get(state, (113, 113, 122))
        img = Image.new("RGB", (64, 64), color)
        return img

    def _notify(self, title: str, message: str, category: str = "") -> None:
        """发送系统通知（通过 notifier 模块，支持去重）。"""
        notifier.notify(title, message, category=category)


def _acquire_lock() -> bool:
    """
    单实例锁：防止多个托盘同时运行。
    使用端口绑定方式实现跨平台锁。
    """
    global _LOCK_SOCKET
    if _LOCK_SOCKET is not None:
        return True

    lock_port = 48901  # 用一个不常见端口作为锁
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", lock_port))
        sock.listen(1)
        # 保持全局引用，防止局部变量释放后锁失效。
        _LOCK_SOCKET = sock
        return True
    except OSError:
        return False


def _release_lock() -> None:
    global _LOCK_SOCKET
    if _LOCK_SOCKET is None:
        return
    try:
        _LOCK_SOCKET.close()
    except Exception:
        pass
    _LOCK_SOCKET = None


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="LarkSync 系统托盘应用",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式：启动 Vite 热重载 + uvicorn --reload",
    )
    return parser.parse_args()


def main() -> None:
    """入口函数。"""
    args = _parse_args()

    if not _acquire_lock():
        print("LarkSync 已在运行中，请勿重复启动。")
        # 尝试打开浏览器让用户看到现有实例
        webbrowser.open(get_dashboard_url())
        return

    if args.dev:
        print("=" * 50)
        print("  LarkSync 开发模式")
        print("  前端: http://localhost:3666 (Vite HMR)")
        print("  后端: http://localhost:8000 (uvicorn --reload)")
        print("  退出: 托盘右键「退出」或 Ctrl+C")
        print("=" * 50)

    app = LarkSyncTray(dev_mode=args.dev)
    try:
        app.run()
    except KeyboardInterrupt:
        pass  # run() 的 finally 会处理清理
    finally:
        _release_lock()
        print("\n正在关闭 LarkSync...")
        app._cleanup_all()


if __name__ == "__main__":
    main()
