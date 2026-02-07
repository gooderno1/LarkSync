@echo off
:: LarkSync 一键启动器 (Windows)
:: 双击此文件启动 LarkSync 系统托盘应用。
:: 自动清理旧进程，确保单实例运行。

cd /d "%~dp0"

:: 清理旧的 LarkSync 进程
echo 正在检查旧进程...
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq LarkSync*" /fo list 2^>nul ^| findstr "PID:"') do (
    taskkill /PID %%i /F >nul 2>&1
)
:: 清理可能残留的 uvicorn (8000端口)
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    echo 清理端口 8000 上的旧进程 (PID %%i)...
    taskkill /PID %%i /F >nul 2>&1
)

:: 等待端口释放
timeout /t 1 /nobreak >nul

:: 优先使用 pythonw（无终端窗口）
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 正在启动 LarkSync...
    start "" pythonw "%~dp0LarkSync.pyw"
    exit
)

:: fallback: 使用 python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 正在启动 LarkSync（终端模式）...
    python "%~dp0LarkSync.pyw"
    exit
)

echo 错误：未找到 Python，请先安装 Python 3.10+ 并添加到 PATH。
echo 下载地址：https://www.python.org/downloads/
pause
