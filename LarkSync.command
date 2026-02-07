#!/bin/bash
# LarkSync 一键启动器 (macOS)
# 双击此文件即可启动 LarkSync 系统托盘应用。
#
# 依赖：
#   pip install pystray Pillow plyer

cd "$(dirname "$0")"
exec python3 -c "from apps.tray.tray_app import main; main()" &
disown
