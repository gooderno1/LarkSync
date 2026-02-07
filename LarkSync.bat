@echo off
:: LarkSync 一键启动器 (Windows)
:: 双击此文件启动 LarkSync 系统托盘应用。
:: 重复启动由程序内的单实例锁自动处理，无需在此清理进程。

cd /d "%~dp0"

:: 优先使用 pythonw（无终端窗口）
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 正在启动 LarkSync...
    start "" pythonw "%~dp0LarkSync.pyw"
    timeout /t 2 /nobreak >nul
    exit
)

:: fallback: 使用 python（保留终端可看日志）
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 正在启动 LarkSync...
    start "LarkSync" python "%~dp0LarkSync.pyw"
    timeout /t 2 /nobreak >nul
    exit
)

echo 错误：未找到 Python，请先安装 Python 3.10+ 并添加到 PATH。
echo 下载地址：https://www.python.org/downloads/
pause
