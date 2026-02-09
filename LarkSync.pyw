#!/usr/bin/env pythonw
"""
LarkSync 一键启动器 (Windows)

双击此文件即可启动 LarkSync 系统托盘应用。
.pyw 扩展名确保 Windows 上不弹出终端窗口。

依赖：
  pip install pystray Pillow plyer
"""

import sys
import os

# 确保项目根目录在 sys.path 中
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from apps.tray.tray_app import main


def _run_backend() -> None:
    """在打包环境中直接启动后端（替代 python -m uvicorn）。"""
    from apps.tray.config import BACKEND_DIR, BACKEND_HOST, BACKEND_PORT
    os.chdir(str(BACKEND_DIR))
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from src.main import app
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT, log_level="warning")

if __name__ == "__main__":
    if "--backend" in sys.argv:
        sys.argv.remove("--backend")
        _run_backend()
        raise SystemExit(0)
    main()
