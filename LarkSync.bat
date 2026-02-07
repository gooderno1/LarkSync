@echo off
:: LarkSync 一键启动器 (Windows)
:: 双击此文件启动 LarkSync 系统托盘应用。
:: 如果 .pyw 双击无效，请使用此 .bat 文件。

cd /d "%~dp0"

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
