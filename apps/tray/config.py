"""托盘应用配置"""

from pathlib import Path
import sys

# ---- 路径 ----
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "apps" / "backend"
FRONTEND_DIR = PROJECT_ROOT / "apps" / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
ICONS_DIR = Path(__file__).resolve().parent / "icons"

# ---- 后端服务 ----
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# ---- 前端开发服务器 ----
VITE_DEV_PORT = 3666
VITE_DEV_URL = f"http://{BACKEND_HOST}:{VITE_DEV_PORT}"

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


def _is_port_active(port: int) -> bool:
    """检测本地端口是否有服务在监听。"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((BACKEND_HOST, port)) == 0


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
