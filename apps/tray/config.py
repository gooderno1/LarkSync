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
def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if 0 < value < 65536 else default


_bind_host_raw = (os.getenv("LARKSYNC_BACKEND_BIND_HOST") or "").strip()
# Windows 默认绑定 0.0.0.0，确保 WSL/OpenClaw 可访问宿主机后端。
# 如需仅本机回环访问，可显式设置 LARKSYNC_BACKEND_BIND_HOST=127.0.0.1
_DEFAULT_BACKEND_BIND_HOST = "0.0.0.0" if sys.platform == "win32" else "127.0.0.1"
BACKEND_HOST = _bind_host_raw or _DEFAULT_BACKEND_BIND_HOST
DEFAULT_BACKEND_PORT = 18765
LEGACY_BACKEND_PORT = 8000
RESERVED_PRODUCTION_BACKEND_PORTS = (DEFAULT_BACKEND_PORT, LEGACY_BACKEND_PORT)
BACKEND_PORT = _int_env("LARKSYNC_BACKEND_PORT", DEFAULT_BACKEND_PORT)
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
VITE_DEV_PORT = _int_env("LARKSYNC_VITE_DEV_PORT", 3666)
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
    返回生产管理面板 URL。

    3666 只属于显式 --dev 模式；安装版即使检测到本机正在运行 Vite，
    也必须走 FastAPI 默认端口挂载的静态前端，避免误打开开发页面。
    """
    return BACKEND_URL


# ---- 浏览器 URL（动态检测） ----
def get_dashboard_url() -> str:
    return f"{_detect_frontend_url()}/"


def get_settings_url() -> str:
    return f"{_detect_frontend_url()}/#settings"


def get_logs_url() -> str:
    return f"{_detect_frontend_url()}/#activity"
