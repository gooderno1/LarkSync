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


def _detect_frontend_url() -> str:
    """
    自动检测前端 URL：
    - 如果 dist/ 目录存在 → 生产模式，用 FastAPI 端口 (8000)
    - 否则 → 开发模式，用 Vite 开发服务器端口 (3666)
    """
    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        return BACKEND_URL
    return VITE_DEV_URL


# ---- 浏览器 URL（动态检测） ----
def get_dashboard_url() -> str:
    return f"{_detect_frontend_url()}/"


def get_settings_url() -> str:
    return f"{_detect_frontend_url()}/#settings"


def get_logs_url() -> str:
    return f"{_detect_frontend_url()}/#logcenter"
