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

if __name__ == "__main__":
    main()
