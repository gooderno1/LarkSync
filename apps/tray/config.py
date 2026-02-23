"""托盘应用配置"""

from pathlib import Path
import os
import sys

# ---- 路径 ----
_BUNDLE_ROOT = None
if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        _BUNDLE_ROOT = Path(meipass).resolve()

PROJECT_ROOT = _BUNDLE_ROOT or Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "apps" / "backend"
FRONTEND_DIR = PROJECT_ROOT / "apps" / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
ICONS_DIR = Path(__file__).resolve().parent / "icons"

# ---- 后端服务 ----
_bind_host_raw = (os.getenv("LARKSYNC_BACKEND_BIND_HOST") or "").strip()
# Windows 默认绑定 0.0.0.0，确保 WSL/OpenClaw 可访问宿主机后端。
# 如需仅本机回环访问，可显式设置 LARKSYNC_BACKEND_BIND_HOST=127.0.0.1
_DEFAULT_BACKEND_BIND_HOST = "0.0.0.0" if sys.platform == "win32" else "127.0.0.1"
BACKEND_HOST = _bind_host_raw or _DEFAULT_BACKEND_BIND_HOST
BACKEND_PORT = 8000
_client_host_raw = (os.getenv("LARKSYNC_BACKEND_CLIENT_HOST") or "").strip()
if _client_host_raw:
    BACKEND_CLIENT_HOST = _client_host_raw
elif BACKEND_HOST in {"0.0.0.0", "::"}:
    # 绑定全网卡时，托盘本机回环访问仍应使用可路由地址。
    BACKEND_CLIENT_HOST = "127.0.0.1"
else:
    BACKEND_CLIENT_HOST = BACKEND_HOST
BACKEND_URL = f"http://{BACKEND_CLIENT_HOST}:{BACKEND_PORT}"

# ---- 前端开发服务器 ----
VITE_DEV_PORT = 3666
# Vite 在 Windows 上默认绑定 IPv6 [::1]，必须用 localhost（自动解析 IPv4/IPv6）
VITE_DEV_URL = f"http://localhost:{VITE_DEV_PORT}"

# ---- 健康检查 ----
HEALTH_CHECK_URL = f"{BACKEND_URL}/health"
HEALTH_CHECK_TIMEOUT = 3  # 秒
STARTUP_WAIT_TIMEOUT = 15  # 等待后端启动的最大秒数
STARTUP_POLL_INTERVAL = 0.5  # 启动轮询间隔

# ---- 状态轮询 ----
STATUS_POLL_INTERVAL = 5  # 秒
TRAY_STATUS_URL = f"{BACKEND_URL}/tray/status"

# ---- 自动重启 ----
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 5  # 秒

# ---- Python 解释器 ----
PYTHON_EXE = sys.executable


def _is_port_active(port: int, host: str = "localhost") -> bool:
    """检测本地端口是否有服务在监听。
    
    默认使用 localhost 以兼容 IPv4 (127.0.0.1) 和 IPv6 ([::1])。
    Vite 在 Windows 上常绑定 [::1]，若用 127.0.0.1 会检测不到。
    """
    import socket
    # getaddrinfo 会返回所有可用地址（IPv4 + IPv6），逐个尝试
    for af, socktype, proto, canonname, sa in socket.getaddrinfo(
        host, port, socket.AF_UNSPEC, socket.SOCK_STREAM
    ):
        try:
            with socket.socket(af, socktype, proto) as s:
                s.settimeout(1)
                if s.connect_ex(sa) == 0:
                    return True
        except OSError:
            continue
    return False


def _detect_frontend_url() -> str:
    """
    自动检测前端 URL（优先级）：
    1. Vite 开发服务器在 3666 运行 → 开发模式，用 3666（最新代码 + HMR）
    2. dist/ 存在且 Vite 未运行 → 生产模式，用 FastAPI 8000
    3. 都没有 → 默认 8000（等用户 build 或启动 --dev）
    """
    if _is_port_active(VITE_DEV_PORT):
        return VITE_DEV_URL
    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        return BACKEND_URL
    return BACKEND_URL


# ---- 浏览器 URL（动态检测） ----
def get_dashboard_url() -> str:
    return f"{_detect_frontend_url()}/"


def get_settings_url() -> str:
    return f"{_detect_frontend_url()}/#settings"


def get_logs_url() -> str:
    return f"{_detect_frontend_url()}/#logcenter"
