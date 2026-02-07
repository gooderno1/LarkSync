"""
LarkSync 系统托盘应用 — 主入口

功能：
- 启动/管理后端 FastAPI 服务
- 系统托盘图标（状态可视化）
- 右键菜单（打开面板/暂停/日志/退出）
- 状态轮询 + 图标动态切换
- 系统通知（冲突/错误）
"""

from __future__ import annotations

import sys
import os
import threading
import time
import webbrowser
import json
import urllib.request
import urllib.error

# 确保项目根目录在 sys.path 中
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apps.tray.config import (
    BACKEND_URL,
    STATUS_POLL_INTERVAL,
    TRAY_STATUS_URL,
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


class LarkSyncTray:
    """LarkSync 系统托盘应用。"""

    def __init__(self) -> None:
        self._backend = BackendManager()
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

        # 先启动后端
        print("正在启动 LarkSync 后端...")
        success = self._backend.start(wait=True)
        if success:
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
        self._icon = pystray.Icon(
            name="LarkSync",
            icon=self._load_icon("idle"),
            title="LarkSync — 同步服务",
            menu=self._build_menu(),
        )
        self._icon.run()

    def stop(self) -> None:
        """退出托盘应用。"""
        self._running = False
        self._backend.stop()
        if self._icon:
            self._icon.stop()

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

    def _on_open_dashboard(self, icon=None, item=None) -> None:
        webbrowser.open(get_dashboard_url())

    def _on_open_settings(self, icon=None, item=None) -> None:
        webbrowser.open(get_settings_url())

    def _on_open_logs(self, icon=None, item=None) -> None:
        webbrowser.open(get_logs_url())

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


def main() -> None:
    """入口函数。"""
    app = LarkSyncTray()
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
