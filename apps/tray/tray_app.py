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
import sys
import os
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

# 确保项目根目录在 sys.path 中
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

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
)
from apps.tray.backend_manager import BackendManager
from apps.tray.icon_generator import generate_icons, get_icon_path
from apps.tray.autostart import is_autostart_enabled, toggle_autostart
from apps.tray import notifier

# ---- 延迟导入 pystray / PIL（可能未安装） ----
try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _is_port_active(port: int) -> bool:
    """检测本地端口是否有服务在监听。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((BACKEND_HOST, port)) == 0


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """等待端口变为可用，返回是否成功。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_port_active(port):
            return True
        time.sleep(0.3)
    return False


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

        # 确保图标已生成
        generate_icons()

    # ---- 公共方法 ----

    def run(self) -> None:
        """启动托盘应用（阻塞式）。"""
        if not HAS_TRAY:
            print("错误：缺少 pystray 或 Pillow，请先安装：")
            print("  pip install pystray Pillow")
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

    # ---- 状态轮询 ----

    def _poll_status_loop(self) -> None:
        """后台线程：定期查询后端状态并更新图标。"""
        while self._running:
            try:
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
    lock_port = 48901  # 用一个不常见端口作为锁
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", lock_port))
        sock.listen(1)
        # 不关闭 sock — 进程退出时自动释放
        return True
    except OSError:
        return False


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
        print("\n正在关闭 LarkSync...")
        app._cleanup_all()


if __name__ == "__main__":
    main()
