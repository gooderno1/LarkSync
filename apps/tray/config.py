"""托盘应用配置"""

from pathlib import Path
import sys

# ---- 路径 ----
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "apps" / "backend"
ICONS_DIR = Path(__file__).resolve().parent / "icons"

# ---- 后端服务 ----
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

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

# ---- 浏览器 URL ----
DASHBOARD_URL = f"{BACKEND_URL}/"
SETTINGS_URL = f"{BACKEND_URL}/#settings"
LOGS_URL = f"{BACKEND_URL}/#logcenter"
