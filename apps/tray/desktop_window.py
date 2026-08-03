"""Desktop window host for the tray application.

The tray process owns backend lifecycle and status polling. The desktop
window runs in a persistent child process so pywebview's GUI event loop does
not compete with pystray's event loop.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal


DEFAULT_WINDOW_TITLE = "LarkSync"
DEFAULT_WINDOW_WIDTH = 1360
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_MIN_WIDTH = 1080
DEFAULT_MIN_HEIGHT = 720
WINDOWS_TITLEBAR_CAPTION_COLOR = "#EAF2F8"
WINDOWS_TITLEBAR_TEXT_COLOR = "#24364F"
WINDOWS_TITLEBAR_BORDER_COLOR = "#B9CBE0"

_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36

_SW_RESTORE = 9
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_SHOWWINDOW = 0x0040
_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2

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


def grant_desktop_window_foreground_permission(
    process_id: int,
    *,
    user32: Any | None = None,
) -> bool:
    """Let the WebView child process activate after a user tray action."""
    if sys.platform != "win32":
        return True
    if process_id <= 0:
        return False
    try:
        windows_api = user32 or ctypes.windll.user32
        return bool(windows_api.AllowSetForegroundWindow(int(process_id)))
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def bring_desktop_window_to_front(
    window: Any,
    *,
    user32: Any | None = None,
    appkit: Any | None = None,
) -> bool:
    """Activate a restored desktop window using the native platform API."""
    if sys.platform == "darwin":
        try:
            cocoa = appkit or importlib.import_module("AppKit")
            cocoa.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            native = getattr(window, "native", None)
            make_key = getattr(native, "makeKeyAndOrderFront_", None)
            if callable(make_key):
                make_key(None)
            return True
        except (AttributeError, ImportError, OSError, TypeError, ValueError):
            return False
    if sys.platform != "win32":
        return True
    try:
        native = window.native
        handle = native.Handle
        hwnd = int(handle.ToInt64()) if hasattr(handle, "ToInt64") else int(handle)
        windows_api = user32 or ctypes.windll.user32

        windows_api.ShowWindowAsync(hwnd, _SW_RESTORE)
        windows_api.BringWindowToTop(hwnd)
        if bool(windows_api.SetForegroundWindow(hwnd)):
            return True

        flags = _SWP_NOMOVE | _SWP_NOSIZE | _SWP_SHOWWINDOW
        raised = bool(
            windows_api.SetWindowPos(hwnd, _HWND_TOPMOST, 0, 0, 0, 0, flags)
        )
        lowered = bool(
            windows_api.SetWindowPos(hwnd, _HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        )
        windows_api.BringWindowToTop(hwnd)
        windows_api.SetForegroundWindow(hwnd)
        foreground = int(windows_api.GetForegroundWindow())
        return foreground == hwnd or (raised and lowered)
    except (AttributeError, OSError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class DesktopWindowLaunchResult:
    opened: bool
    mode: LaunchMode
    url: str
    message: str = ""
    pid: int | None = None
    process: Any | None = None
    control_file: Path | None = None


def _schedule_daemon(action: Callable[[], Any]) -> None:
    threading.Thread(target=action, name="larksync-window-action", daemon=True).start()


def _make_hide_on_close_handler(
    window: Any,
    *,
    scheduler: Callable[[Callable[[], Any]], None] = _schedule_daemon,
) -> Callable[[], bool]:
    """Convert the native close button into hide-to-tray.

    pywebview invokes the locked ``closing`` event on the GUI thread. Hiding
    from a daemon thread lets the handler return ``False`` first, which
    cancels destruction without deadlocking the WinForms dispatcher.
    """

    def _hide_on_close() -> bool:
        scheduler(window.hide)
        return False

    return _hide_on_close


def _start_macos_reopen_monitor(window: Any, *, appkit: Any | None = None) -> None:
    """Dock 再次激活隐藏的应用时恢复窗口，不干扰关闭到托盘行为。"""
    if sys.platform != "darwin" or getattr(window, "_larksync_reopen_monitor", False):
        return
    setattr(window, "_larksync_reopen_monitor", True)

    def monitor() -> None:  # pragma: no cover - requires Cocoa event loop
        try:
            cocoa = appkit or importlib.import_module("AppKit")
            application = cocoa.NSApplication.sharedApplication()
            was_active = bool(application.isActive())
            while True:
                time.sleep(0.2)
                active = bool(application.isActive())
                native = getattr(window, "native", None)
                visible_reader = getattr(native, "isVisible", None)
                visible = bool(visible_reader()) if callable(visible_reader) else True
                if active and not was_active and not visible:
                    window.restore()
                    window.show()
                    bring_desktop_window_to_front(window, appkit=cocoa)
                was_active = active
        except Exception:
            return

    threading.Thread(target=monitor, name="larksync-macos-reopen", daemon=True).start()


class DesktopWindowControlServer:
    """Small authenticated loopback channel used by the tray to reuse a window."""

    def __init__(
        self,
        window: Any,
        control_file: Path,
        *,
        foreground_activator: Callable[[Any], bool] = bring_desktop_window_to_front,
    ) -> None:
        self._window = window
        self._control_file = Path(control_file)
        self._foreground_activator = foreground_activator
        self._token = secrets.token_urlsafe(32)
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    def start(self) -> None:
        if self._socket is not None:
            return
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(4)
        listener.settimeout(0.2)
        self._socket = listener
        port = int(listener.getsockname()[1])
        self._write_descriptor(port)
        self._thread = threading.Thread(
            target=self._serve,
            name="larksync-window-control",
            daemon=True,
        )
        self._thread.start()

    def _write_descriptor(self, port: int) -> None:
        self._control_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._control_file.with_suffix(f"{self._control_file.suffix}.tmp")
        temporary.write_text(
            json.dumps(
                {"pid": os.getpid(), "port": port, "token": self._token},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(self._control_file)

    def _serve(self) -> None:
        listener = self._socket
        if listener is None:
            return
        while not self._stopping.is_set():
            try:
                connection, _address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                connection.settimeout(0.5)
                try:
                    payload = json.loads(connection.recv(65536).decode("utf-8"))
                    if payload.get("token") != self._token:
                        raise PermissionError("invalid desktop control token")
                    if payload.get("action") != "show":
                        raise ValueError("unsupported desktop control action")
                    url = str(payload.get("url") or "").strip()
                    if url:
                        self._window.load_url(url)
                    self._window.restore()
                    self._window.show()
                    self._foreground_activator(self._window)
                    response = {"ok": True}
                except Exception as exc:
                    response = {"ok": False, "error": type(exc).__name__}
                try:
                    connection.sendall(json.dumps(response).encode("utf-8"))
                except OSError:
                    pass

    def stop(self) -> None:
        self._stopping.set()
        listener = self._socket
        self._socket = None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._thread = None
        self._control_file.unlink(missing_ok=True)


def send_desktop_window_command(
    control_file: Path,
    *,
    url: str,
    timeout: float = 0.5,
) -> bool:
    """Restore, focus and optionally navigate the already-running window."""
    try:
        descriptor = json.loads(Path(control_file).read_text(encoding="utf-8"))
        port = int(descriptor["port"])
        token = str(descriptor["token"])
        request = json.dumps({"action": "show", "url": url, "token": token}).encode("utf-8")
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as connection:
            connection.settimeout(timeout)
            connection.sendall(request)
            response = json.loads(connection.recv(4096).decode("utf-8"))
        return response.get("ok") is True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _new_control_file() -> Path:
    return Path(tempfile.gettempdir()) / (
        f"larksync-desktop-{os.getpid()}-{uuid.uuid4().hex}.json"
    )


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
    control_file: Path | None = None,
) -> list[str]:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    python_executable = executable or sys.executable
    command = [python_executable]
    if not is_frozen:
        command.append(str(tray_app_path or (Path(__file__).resolve().parent / "launcher.py")))
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
    if control_file is not None:
        command.extend(["--control-file", str(control_file)])
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
    startup_grace_seconds: float = 0,
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

    control_file = _new_control_file()
    command = _desktop_window_command(
        url,
        title=title,
        width=width,
        height=height,
        min_width=min_width,
        min_height=min_height,
        debug=debug,
        control_file=control_file,
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
        control_file=control_file,
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
    control_file: Path | None = None,
    smoke_result: Path | None = None,
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
    if sys.platform == "darwin" and getattr(getattr(window, "events", None), "shown", None) is not None:
        window.events.shown += lambda: bring_desktop_window_to_front(window)
        window.events.shown += lambda: _start_macos_reopen_monitor(window)
    closing_event = getattr(getattr(window, "events", None), "closing", None)
    if closing_event is not None:
        window.events.closing += _make_hide_on_close_handler(window)
    control_server = (
        DesktopWindowControlServer(window, control_file)
        if control_file is not None
        else None
    )
    shown_event = getattr(getattr(window, "events", None), "shown", None)
    if control_server is not None and shown_event is not None:
        window.events.shown += control_server.start
    loaded_event = getattr(getattr(window, "events", None), "loaded", None)
    if smoke_result is not None and loaded_event is not None:
        window.events.loaded += lambda: _schedule_daemon(
            lambda: _run_ui_smoke_probe(window, Path(smoke_result))
        )
    start_kwargs: dict[str, Any] = {"debug": debug}
    if sys.platform == "win32":
        start_kwargs["gui"] = "edgechromium"
    try:
        try:
            webview.start(**start_kwargs)
        except TypeError:
            start_kwargs.pop("gui", None)
            webview.start(**start_kwargs)
    finally:
        if control_server is not None:
            control_server.stop()
    return 0


def _run_ui_smoke_probe(window: Any, result_path: Path, timeout: float = 30.0) -> None:
    """在真实 WebView 中验证首屏和二维码，并输出机器可读结果。"""
    deadline = time.time() + max(timeout, 0.1)
    last_result: dict[str, Any] = {}
    last_error = ""
    script = """
        (() => {
          const root = document.querySelector('[data-onboarding-root="true"]');
          const panel = document.querySelector('[data-testid="oauth-qr-panel"]');
          const image = document.querySelector('[data-testid="oauth-qr-image"]');
          const rect = image ? image.getBoundingClientRect() : null;
          return {
            title: document.title,
            onboarding_visible: Boolean(root),
            qr_state: panel ? panel.getAttribute('data-qr-state') : null,
            qr_visible: Boolean(rect && rect.width > 0 && rect.height > 0),
            qr_is_data_url: Boolean(image && String(image.getAttribute('src') || '').startsWith('data:image/png;base64,'))
          };
        })()
    """
    while time.time() < deadline:
        try:
            payload = window.evaluate_js(script)
            if isinstance(payload, dict):
                last_result = payload
                if _ui_smoke_result_ok(payload):
                    break
        except Exception as exc:  # pragma: no cover - native WebView only
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.25)
    result = {**last_result, "ok": _ui_smoke_result_ok(last_result), "error": last_error}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def _ui_smoke_result_ok(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("onboarding_visible")
        and payload.get("qr_state") == "ready"
        and payload.get("qr_visible")
        and payload.get("qr_is_data_url")
    )


def parse_desktop_window_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LarkSync 桌面窗口宿主")
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", default=DEFAULT_WINDOW_TITLE)
    parser.add_argument("--width", type=int, default=DEFAULT_WINDOW_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_WINDOW_HEIGHT)
    parser.add_argument("--min-width", type=int, default=DEFAULT_MIN_WIDTH)
    parser.add_argument("--min-height", type=int, default=DEFAULT_MIN_HEIGHT)
    parser.add_argument("--debug-window", "--debug", dest="debug", action="store_true")
    parser.add_argument("--control-file", type=Path)
    parser.add_argument("--smoke-result", type=Path, help=argparse.SUPPRESS)
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
        control_file=args.control_file,
        smoke_result=args.smoke_result,
    )


if __name__ == "__main__":
    raise SystemExit(main())
