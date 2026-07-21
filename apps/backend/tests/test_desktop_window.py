import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import desktop_window
from apps.tray import tray_app


def test_default_window_size_matches_normal_desktop_readability_target() -> None:
    assert desktop_window.DEFAULT_WINDOW_WIDTH == 1360
    assert desktop_window.DEFAULT_WINDOW_HEIGHT == 900
    assert desktop_window.DEFAULT_MIN_WIDTH == 1080
    assert desktop_window.DEFAULT_MIN_HEIGHT == 720


def test_tray_internal_window_parser_uses_desktop_defaults(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["larksync"])

    args = tray_app._parse_args()

    assert args.width == desktop_window.DEFAULT_WINDOW_WIDTH
    assert args.height == desktop_window.DEFAULT_WINDOW_HEIGHT
    assert args.min_width == desktop_window.DEFAULT_MIN_WIDTH
    assert args.min_height == desktop_window.DEFAULT_MIN_HEIGHT


def test_open_desktop_window_falls_back_to_browser_when_webview_missing() -> None:
    opened: list[str] = []

    result = desktop_window.open_desktop_window(
        "http://127.0.0.1:8000/",
        webview_probe=lambda: False,
        browser_opener=lambda url: opened.append(url),
    )

    assert result.opened is True
    assert result.mode == "browser"
    assert "pywebview" in result.message
    assert opened == ["http://127.0.0.1:8000/"]


def test_open_desktop_window_spawns_child_process_when_webview_is_available() -> None:
    commands: list[list[str]] = []

    class FakeProcess:
        pid = 4242

    def fake_popen(command, **_kwargs):
        commands.append(command)
        return FakeProcess()

    result = desktop_window.open_desktop_window(
        "http://127.0.0.1:8000/",
        title="LarkSync Test",
        width=1200,
        height=760,
        min_width=1000,
        min_height=700,
        debug=True,
        webview_probe=lambda: True,
        popen_factory=fake_popen,
        startup_grace_seconds=0,
    )

    assert result.mode == "webview"
    assert result.pid == 4242
    assert commands
    command = commands[0]
    assert "--desktop-window" in command
    assert "--url" in command
    assert "http://127.0.0.1:8000/" in command
    assert "--debug-window" in command
    assert "--debug" not in command


def test_open_desktop_window_falls_back_when_child_exits_immediately() -> None:
    opened: list[str] = []

    class ExitedProcess:
        pid = 42

        def poll(self):
            return 1

    result = desktop_window.open_desktop_window(
        "http://127.0.0.1:8000/",
        webview_probe=lambda: True,
        popen_factory=lambda *_args, **_kwargs: ExitedProcess(),
        browser_opener=lambda url: opened.append(url),
        startup_grace_seconds=0.01,
    )

    assert result.mode == "browser"
    assert "提前退出" in result.message
    assert opened == ["http://127.0.0.1:8000/"]


def test_run_desktop_window_creates_expected_window(monkeypatch) -> None:
    events: list[tuple[str, tuple, dict]] = []
    shown_callbacks: list[object] = []

    class FakeShownEvent:
        def __iadd__(self, callback):
            shown_callbacks.append(callback)
            return self

    class FakeWindow:
        class Events:
            shown = FakeShownEvent()

        events = Events()

    class FakeWebview:
        def create_window(self, *args, **kwargs):
            events.append(("create_window", args, kwargs))
            return FakeWindow()

        def start(self, **kwargs):
            events.append(("start", (), kwargs))

    monkeypatch.setattr(desktop_window.sys, "platform", "win32")

    exit_code = desktop_window.run_desktop_window(
        "http://127.0.0.1:8000/",
        title="LarkSync Test",
        width=1280,
        height=820,
        min_width=1080,
        min_height=720,
        webview_module=FakeWebview(),
    )

    assert exit_code == 0
    assert events[0][0] == "create_window"
    assert events[0][1][:2] == ("LarkSync Test", "http://127.0.0.1:8000/")
    assert events[0][2]["width"] == 1280
    assert events[0][2]["height"] == 820
    assert events[0][2]["min_size"] == (1080, 720)
    assert events[0][2]["frameless"] is False
    assert events[0][2]["easy_drag"] is False
    assert events[0][2]["background_color"] == "#F5FAFF"
    assert shown_callbacks == [desktop_window._apply_windows_titlebar_palette]
    assert events[1] == ("start", (), {"debug": False, "gui": "edgechromium"})


def test_windows_titlebar_palette_uses_subtle_cool_contrast() -> None:
    assert desktop_window.WINDOWS_TITLEBAR_CAPTION_COLOR == "#EAF2F8"
    assert desktop_window.WINDOWS_TITLEBAR_TEXT_COLOR == "#24364F"
    assert desktop_window.WINDOWS_TITLEBAR_BORDER_COLOR == "#B9CBE0"
    assert desktop_window._colorref_from_hex("#EAF2F8") == 0x00F8F2EA


def test_tray_default_open_uses_desktop_window(monkeypatch) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)
    tray._dev_mode = False

    opened: list[str] = []
    browsers: list[str] = []
    monkeypatch.setattr(tray_app, "get_dashboard_url", lambda: "http://127.0.0.1:8000/")
    monkeypatch.setattr(tray_app, "open_desktop_window", lambda url: opened.append(url))
    monkeypatch.setattr(tray_app, "open_browser_dashboard", lambda url: browsers.append(url))

    tray._on_open_desktop_window()
    tray._on_open_browser_dashboard()

    assert opened == ["http://127.0.0.1:8000/"]
    assert browsers == ["http://127.0.0.1:8000/"]


def test_tray_reuses_running_desktop_window(monkeypatch) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)

    class RunningProcess:
        pid = 9001

        def poll(self):
            return None

    existing = RunningProcess()
    tray._desktop_window_process = existing
    opened: list[str] = []
    monkeypatch.setattr(
        tray_app,
        "open_desktop_window",
        lambda url: opened.append(url),
    )

    result = tray._open_desktop_window("http://127.0.0.1:8000/#settings")

    assert result.mode == "webview"
    assert result.pid == 9001
    assert result.message == "桌面窗口已在运行。"
    assert opened == []


def test_tray_reopens_desktop_window_after_previous_window_exited(monkeypatch) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)

    class ExitedProcess:
        pid = 9001

        def poll(self):
            return 0

    class NewProcess:
        pid = 9002

        def poll(self):
            return None

    tray._desktop_window_process = ExitedProcess()
    new_process = NewProcess()

    def fake_open(url):
        return desktop_window.DesktopWindowLaunchResult(
            opened=True,
            mode="webview",
            url=url,
            pid=new_process.pid,
            process=new_process,
        )

    monkeypatch.setattr(tray_app, "open_desktop_window", fake_open)

    result = tray._open_desktop_window("http://127.0.0.1:8000/#activity")

    assert result.mode == "webview"
    assert result.pid == 9002
    assert tray._desktop_window_process is new_process


def test_tray_stop_desktop_window_kills_running_process(monkeypatch) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)
    killed: list[int] = []
    waited: list[int] = []

    class RunningProcess:
        pid = 9001

        def poll(self):
            return None

        def wait(self, timeout):
            waited.append(timeout)

    tray._desktop_window_process = RunningProcess()
    monkeypatch.setattr(tray_app, "_kill_process_tree", lambda pid: killed.append(pid))

    tray._stop_desktop_window()

    assert killed == [9001]
    assert waited == [5]
    assert tray._desktop_window_process is None


def test_tray_route_actions_prefer_desktop_window(monkeypatch) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)
    tray._dev_mode = False

    opened: list[str] = []
    browser_opened: list[str] = []
    monkeypatch.setattr(tray_app, "get_dashboard_url", lambda: "http://127.0.0.1:8000/")
    monkeypatch.setattr(tray_app, "open_desktop_window", lambda url: opened.append(url))
    monkeypatch.setattr(tray_app.webbrowser, "open", lambda url: browser_opened.append(url))

    tray._on_open_settings()
    tray._on_open_logs()

    assert opened == [
        "http://127.0.0.1:8000/#settings",
        "http://127.0.0.1:8000/#activity",
    ]
    assert browser_opened == []


def test_duplicate_tray_launch_opens_desktop_window(monkeypatch) -> None:
    opened: list[str] = []
    browser_opened: list[str] = []

    monkeypatch.setattr(tray_app.sys, "argv", ["tray_app.py"])
    monkeypatch.setattr(tray_app, "_acquire_lock", lambda: False)
    monkeypatch.setattr(tray_app, "get_dashboard_url", lambda: "http://127.0.0.1:8000/")
    monkeypatch.setattr(tray_app, "open_desktop_window", lambda url: opened.append(url))
    monkeypatch.setattr(tray_app.webbrowser, "open", lambda url: browser_opened.append(url))

    tray_app.main()

    assert opened == ["http://127.0.0.1:8000/"]
    assert browser_opened == []
