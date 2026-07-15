"""Windows desktop window host for the tray application.

The tray process owns backend lifecycle and status polling. The desktop
window runs in a short-lived child process so pywebview's GUI event loop does
not compete with pystray's event loop.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib
import importlib.util
import os
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal


DEFAULT_WINDOW_TITLE = "LarkSync"
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 820
DEFAULT_MIN_WIDTH = 1080
DEFAULT_MIN_HEIGHT = 720
WINDOWS_TITLEBAR_CAPTION_COLOR = "#EAF2F8"
WINDOWS_TITLEBAR_TEXT_COLOR = "#24364F"
WINDOWS_TITLEBAR_BORDER_COLOR = "#B9CBE0"

_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36

LaunchMode = Literal["webview", "browser"]


def _colorref_from_hex(value: str) -> int:
    """Convert an RGB hex color to the BGR COLORREF expected by DWM."""
    normalized = value.strip().lstrip("#")
    if len(normalized) != 6:
        raise ValueError(f"Expected a six-digit RGB color, got {value!r}")
    red = int(normalized[0:2], 16)
    green = int(normalized[2:4], 16)
    blue = int(normalized[4:6], 16)
    return red | (green << 8) | (blue << 16)


def _apply_windows_titlebar_palette(window: Any) -> None:
    """Apply a subtle native caption palette while preserving system chrome."""
    if sys.platform != "win32":
        return
    try:
        native = window.native
        hwnd = int(native.Handle.ToInt64())
        setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
        for attribute, color in (
            (_DWMWA_BORDER_COLOR, WINDOWS_TITLEBAR_BORDER_COLOR),
            (_DWMWA_CAPTION_COLOR, WINDOWS_TITLEBAR_CAPTION_COLOR),
            (_DWMWA_TEXT_COLOR, WINDOWS_TITLEBAR_TEXT_COLOR),
        ):
            colorref = ctypes.c_int(_colorref_from_hex(color))
            setter(hwnd, attribute, ctypes.byref(colorref), ctypes.sizeof(colorref))
    except (AttributeError, OSError, TypeError, ValueError):
        # Older Windows builds may not support caption color attributes.
        return


@dataclass(frozen=True)
class DesktopWindowLaunchResult:
    opened: bool
    mode: LaunchMode
    url: str
    message: str = ""
    pid: int | None = None
    process: Any | None = None


def _truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def webview_available() -> bool:
    """Return whether pywebview's import module is available."""
    return importlib.util.find_spec("webview") is not None


def open_browser_dashboard(
    url: str,
    *,
    browser_opener: Callable[[str], Any] = webbrowser.open,
) -> DesktopWindowLaunchResult:
    browser_opener(url)
    return DesktopWindowLaunchResult(
        opened=True,
        mode="browser",
        url=url,
        message="已使用浏览器 fallback 打开桌面工作台。",
    )


def _desktop_window_command(
    url: str,
    *,
    title: str,
    width: int,
    height: int,
    min_width: int,
    min_height: int,
    debug: bool = False,
    frozen: bool | None = None,
    executable: str | None = None,
    tray_app_path: Path | None = None,
) -> list[str]:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    python_executable = executable or sys.executable
    command = [python_executable]
    if not is_frozen:
        command.append(str(tray_app_path or (Path(__file__).resolve().parent / "tray_app.py")))
    command.extend(
        [
            "--desktop-window",
            "--url",
            url,
            "--title",
            title,
            "--width",
            str(width),
            "--height",
            str(height),
            "--min-width",
            str(min_width),
            "--min-height",
            str(min_height),
        ]
    )
    if debug:
        command.append("--debug-window")
    return command


def _desktop_window_creationflags() -> int:
    if sys.platform != "win32":
        return 0
    return (
        getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )


def open_desktop_window(
    url: str,
    *,
    title: str = DEFAULT_WINDOW_TITLE,
    width: int = DEFAULT_WINDOW_WIDTH,
    height: int = DEFAULT_WINDOW_HEIGHT,
    min_width: int = DEFAULT_MIN_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    debug: bool = False,
    browser_opener: Callable[[str], Any] = webbrowser.open,
    popen_factory: Callable[..., subprocess.Popen[Any]] = subprocess.Popen,
    webview_probe: Callable[[], bool] = webview_available,
    startup_grace_seconds: float = 0.4,
) -> DesktopWindowLaunchResult:
    """Launch the desktop window, falling back to the browser when needed."""
    if _truthy_env(os.getenv("LARKSYNC_FORCE_BROWSER")):
        result = open_browser_dashboard(url, browser_opener=browser_opener)
        return DesktopWindowLaunchResult(
            opened=result.opened,
            mode=result.mode,
            url=url,
            message="已按 LARKSYNC_FORCE_BROWSER 强制使用浏览器 fallback。",
        )

    if not webview_probe():
        result = open_browser_dashboard(url, browser_opener=browser_opener)
        return DesktopWindowLaunchResult(
            opened=result.opened,
            mode=result.mode,
            url=url,
            message="未检测到 pywebview/webview 模块，已回退浏览器。",
        )

    command = _desktop_window_command(
        url,
        title=title,
        width=width,
        height=height,
        min_width=min_width,
        min_height=min_height,
        debug=debug,
    )
    try:
        process = popen_factory(
            command,
            close_fds=True,
            creationflags=_desktop_window_creationflags(),
        )
    except Exception as exc:
        result = open_browser_dashboard(url, browser_opener=browser_opener)
        return DesktopWindowLaunchResult(
            opened=result.opened,
            mode=result.mode,
            url=url,
            message=f"桌面窗口启动失败，已回退浏览器：{type(exc).__name__}: {exc}",
        )

    if hasattr(process, "poll") and startup_grace_seconds > 0:
        time.sleep(startup_grace_seconds)
        exit_code = process.poll()
        if exit_code is not None:
            result = open_browser_dashboard(url, browser_opener=browser_opener)
            return DesktopWindowLaunchResult(
                opened=result.opened,
                mode=result.mode,
                url=url,
                message=f"桌面窗口进程提前退出，已回退浏览器：exit={exit_code}",
            )

    return DesktopWindowLaunchResult(
        opened=True,
        mode="webview",
        url=url,
        pid=getattr(process, "pid", None),
        process=process,
        message="已打开桌面窗口。",
    )


def run_desktop_window(
    url: str,
    *,
    title: str = DEFAULT_WINDOW_TITLE,
    width: int = DEFAULT_WINDOW_WIDTH,
    height: int = DEFAULT_WINDOW_HEIGHT,
    min_width: int = DEFAULT_MIN_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    debug: bool = False,
    webview_module: Any | None = None,
) -> int:
    """Run a blocking pywebview window process."""
    webview = webview_module or importlib.import_module("webview")
    window_kwargs: dict[str, Any] = {
        "width": width,
        "height": height,
        "min_size": (min_width, min_height),
        "confirm_close": False,
        # Keep the Windows system frame until custom chrome also restores
        # edge resizing, snap layouts, the system menu, and accessibility.
        "frameless": False,
        "easy_drag": False,
        "background_color": "#F5FAFF",
    }
    try:
        window = webview.create_window(title, url, **window_kwargs)
    except TypeError:
        window_kwargs.pop("confirm_close", None)
        window = webview.create_window(title, url, **window_kwargs)
    if sys.platform == "win32" and getattr(getattr(window, "events", None), "shown", None) is not None:
        window.events.shown += _apply_windows_titlebar_palette
    start_kwargs: dict[str, Any] = {"debug": debug}
    if sys.platform == "win32":
        start_kwargs["gui"] = "edgechromium"
    try:
        webview.start(**start_kwargs)
    except TypeError:
        start_kwargs.pop("gui", None)
        webview.start(**start_kwargs)
    return 0


def parse_desktop_window_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LarkSync 桌面窗口宿主")
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", default=DEFAULT_WINDOW_TITLE)
    parser.add_argument("--width", type=int, default=DEFAULT_WINDOW_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_WINDOW_HEIGHT)
    parser.add_argument("--min-width", type=int, default=DEFAULT_MIN_WIDTH)
    parser.add_argument("--min-height", type=int, default=DEFAULT_MIN_HEIGHT)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_desktop_window_args(argv)
    return run_desktop_window(
        args.url,
        title=args.title,
        width=args.width,
        height=args.height,
        min_width=args.min_width,
        min_height=args.min_height,
        debug=args.debug,
    )


if __name__ == "__main__":
    raise SystemExit(main())
