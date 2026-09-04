import json
import sys
import time
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
    assert "--control-file" in command
    assert result.control_file is not None


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
    closing_callbacks: list[object] = []

    class FakeShownEvent:
        def __iadd__(self, callback):
            shown_callbacks.append(callback)
            return self

    class FakeClosingEvent:
        def __iadd__(self, callback):
            closing_callbacks.append(callback)
            return self

    class FakeWindow:
        class Events:
            shown = FakeShownEvent()
            closing = FakeClosingEvent()

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
    assert desktop_window._apply_windows_titlebar_palette in shown_callbacks
    assert len(closing_callbacks) == 1
    assert events[1] == ("start", (), {"debug": False, "gui": "edgechromium"})


def test_close_button_hides_window_instead_of_ending_host(monkeypatch) -> None:
    hidden: list[bool] = []

    class FakeWindow:
        def hide(self) -> None:
            hidden.append(True)

    monkeypatch.setattr(desktop_window.sys, "platform", "win32")

    callback = desktop_window._make_hide_on_close_handler(
        FakeWindow(),
        scheduler=lambda action: action(),
    )

    assert callback() is False
    assert hidden == [True]


def test_macos_close_hides_application_on_cocoa_main_thread(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    scheduled: list[object] = []

    class FakeApplication:
        def hide_(self, sender) -> None:
            calls.append(("hide_app", sender))

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    class FakeAppKit:
        NSApplication = FakeNSApplication

    class FakeAppHelper:
        @staticmethod
        def callAfter(callback) -> None:
            scheduled.append(callback)

    class FakeWindow:
        def hide(self) -> None:
            calls.append(("hide_window", None))

    monkeypatch.setattr(desktop_window.sys, "platform", "darwin")

    callback = desktop_window._make_hide_on_close_handler(
        FakeWindow(),
        appkit=FakeAppKit(),
        app_helper=FakeAppHelper(),
    )

    assert callback() is False
    assert calls == []
    assert len(scheduled) == 1
    scheduled[0]()
    assert calls == [("hide_app", None)]


def test_grant_desktop_window_foreground_permission_targets_child_process(monkeypatch) -> None:
    calls: list[int] = []

    class FakeUser32:
        def AllowSetForegroundWindow(self, pid: int) -> int:
            calls.append(pid)
            return 1

    monkeypatch.setattr(desktop_window.sys, "platform", "win32")

    assert desktop_window.grant_desktop_window_foreground_permission(
        4242,
        user32=FakeUser32(),
    ) is True
    assert calls == [4242]


def test_bring_desktop_window_to_front_uses_temporary_topmost_fallback(monkeypatch) -> None:
    hwnd = 0x1234
    calls: list[tuple[str, int]] = []

    class FakeHandle:
        def ToInt64(self) -> int:
            return hwnd

    class FakeNative:
        Handle = FakeHandle()

    class FakeWindow:
        native = FakeNative()

    class FakeUser32:
        def ShowWindowAsync(self, target: int, command: int) -> int:
            assert target == hwnd
            calls.append(("show", command))
            return 1

        def SetForegroundWindow(self, target: int) -> int:
            assert target == hwnd
            calls.append(("foreground", target))
            return 0

        def BringWindowToTop(self, target: int) -> int:
            assert target == hwnd
            calls.append(("bring_to_top", target))
            return 1

        def SetWindowPos(
            self,
            target: int,
            insert_after: int,
            _x: int,
            _y: int,
            _width: int,
            _height: int,
            _flags: int,
        ) -> int:
            assert target == hwnd
            calls.append(("window_pos", insert_after))
            return 1

        def GetForegroundWindow(self) -> int:
            return hwnd

    monkeypatch.setattr(desktop_window.sys, "platform", "win32")

    assert desktop_window.bring_desktop_window_to_front(
        FakeWindow(),
        user32=FakeUser32(),
    ) is True
    assert ("window_pos", desktop_window._HWND_TOPMOST) in calls
    assert ("window_pos", desktop_window._HWND_NOTOPMOST) in calls
    assert calls.index(
        ("window_pos", desktop_window._HWND_TOPMOST)
    ) < calls.index(("window_pos", desktop_window._HWND_NOTOPMOST))


def test_bring_desktop_window_to_front_activates_macos_app(monkeypatch) -> None:
    calls: list[object] = []
    scheduled: list[object] = []

    class FakeApplication:
        def unhide_(self, sender) -> None:
            calls.append(("unhide", sender))

        def activateIgnoringOtherApps_(self, value: bool) -> None:
            calls.append(("activate", value))

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    class FakeAppKit:
        NSApplication = FakeNSApplication

    class FakeAppHelper:
        @staticmethod
        def callAfter(callback) -> None:
            scheduled.append(callback)

    class FakeNative:
        def makeKeyAndOrderFront_(self, sender) -> None:
            calls.append(("front", sender))

    class FakeWindow:
        native = FakeNative()

    monkeypatch.setattr(desktop_window.sys, "platform", "darwin")

    assert desktop_window.bring_desktop_window_to_front(
        FakeWindow(),
        appkit=FakeAppKit(),
        app_helper=FakeAppHelper(),
    ) is True
    assert calls == []
    assert len(scheduled) == 1
    scheduled[0]()
    assert calls == [("unhide", None), ("activate", True), ("front", None)]


def test_configure_macos_tray_as_accessory_app(monkeypatch) -> None:
    calls: list[int] = []

    class FakeApplication:
        def setActivationPolicy_(self, policy: int) -> bool:
            calls.append(policy)
            return True

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    class FakeAppKit:
        NSApplication = FakeNSApplication
        NSApplicationActivationPolicyAccessory = 1

    monkeypatch.setattr(tray_app.sys, "platform", "darwin")

    assert tray_app._configure_macos_tray_activation_policy(appkit=FakeAppKit()) is True
    assert calls == [1]


def test_install_macos_quit_delegate_runs_on_cocoa_main_thread(monkeypatch) -> None:
    scheduled: list[object] = []
    installed: list[object] = []
    delegate = object()
    on_quit = lambda: None

    class FakeApplication:
        def setDelegate_(self, value) -> None:
            installed.append(value)

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    class FakeAppKit:
        NSApplication = FakeNSApplication

    class FakeAppHelper:
        @staticmethod
        def callAfter(callback) -> None:
            scheduled.append(callback)

    monkeypatch.setattr(desktop_window.sys, "platform", "darwin")
    monkeypatch.setattr(desktop_window, "_MACOS_QUIT_DELEGATE", None)
    monkeypatch.setattr(desktop_window, "_MACOS_QUIT_CALLBACK", None)

    assert desktop_window._install_macos_quit_delegate(
        on_quit=on_quit,
        appkit=FakeAppKit(),
        app_helper=FakeAppHelper(),
        delegate_factory=lambda: delegate,
    ) is True
    assert installed == []
    assert len(scheduled) == 1

    scheduled[0]()

    assert installed == [delegate]
    assert desktop_window._MACOS_QUIT_DELEGATE is delegate
    assert desktop_window._MACOS_QUIT_CALLBACK is on_quit


def test_macos_quit_delegate_allows_termination_and_invokes_callback(monkeypatch) -> None:
    installed: list[object] = []
    quit_calls: list[bool] = []
    reopen_calls: list[bool] = []

    class FakeNSObject:
        @classmethod
        def alloc(cls):
            return cls()

        def init(self):
            return self

    class FakeFoundation:
        NSObject = FakeNSObject
        YES = True

    class FakeApplication:
        def setDelegate_(self, value) -> None:
            installed.append(value)

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    class FakeAppKit:
        NSApplication = FakeNSApplication

    class ImmediateAppHelper:
        @staticmethod
        def callAfter(callback) -> None:
            callback()

    monkeypatch.setattr(desktop_window.sys, "platform", "darwin")
    monkeypatch.setattr(desktop_window, "_MACOS_QUIT_DELEGATE", None)
    monkeypatch.setattr(desktop_window, "_MACOS_QUIT_DELEGATE_CLASS", None)
    monkeypatch.setattr(desktop_window, "_MACOS_QUIT_CALLBACK", None)
    monkeypatch.setattr(desktop_window, "_MACOS_REOPEN_CALLBACK", None)

    assert desktop_window._install_macos_quit_delegate(
        on_quit=lambda: quit_calls.append(True),
        on_reopen=lambda: reopen_calls.append(True),
        appkit=FakeAppKit(),
        app_helper=ImmediateAppHelper(),
        foundation=FakeFoundation(),
    ) is True
    assert len(installed) == 1

    delegate = installed[0]
    assert delegate.applicationShouldTerminate_(None) is True
    assert delegate.applicationSupportsSecureRestorableState_(None) is True
    assert delegate.applicationShouldHandleReopen_hasVisibleWindows_(None, False) is True
    assert quit_calls == [True]
    assert reopen_calls == [True]


def test_ui_smoke_probe_writes_success_result(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    destroyed: list[bool] = []

    class FakeWindow:
        def evaluate_js(self, script: str):
            assert 'data-account-connect-root="true"' in script
            assert 'data-testid="start-two-step-connect"' in script
            assert 'img[alt="LarkSync"]' in script
            return {
                "account_connect_visible": True,
                "connect_phase": "choose_method",
                "connect_action_visible": True,
                "connect_action_enabled": True,
                "logo_visible": True,
                "logo_decoded": True,
            }

        def destroy(self) -> None:
            destroyed.append(True)

    desktop_window._run_ui_smoke_probe(FakeWindow(), result_path, timeout=0.1)

    assert '"ok": true' in result_path.read_text(encoding="utf-8")
    assert destroyed == [True]


def test_run_desktop_window_records_smoke_failure_if_native_loop_returns_early(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "result.json"

    class FakeEvent:
        def __iadd__(self, _callback):
            return self

    class FakeWindow:
        class Events:
            shown = FakeEvent()
            closing = FakeEvent()
            loaded = FakeEvent()

        events = Events()

    class FakeWebview:
        def create_window(self, *_args, **_kwargs):
            return FakeWindow()

        def start(self, **_kwargs):
            return None

    exit_code = desktop_window.run_desktop_window(
        "http://127.0.0.1:18765/",
        smoke_result=result_path,
        webview_module=FakeWebview(),
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["completed"] is True
    assert payload["ok"] is False
    assert payload["stage"] == "webview_exited"


def test_control_server_restores_and_navigates_existing_window(tmp_path: Path) -> None:
    actions: list[tuple[str, str | None]] = []

    class FakeWindow:
        def load_url(self, url: str) -> None:
            actions.append(("load_url", url))

        def restore(self) -> None:
            actions.append(("restore", None))

        def show(self) -> None:
            actions.append(("show", None))

    control_file = tmp_path / "desktop-control.json"
    server = desktop_window.DesktopWindowControlServer(
        FakeWindow(),
        control_file,
        foreground_activator=lambda _window: actions.append(("bring_to_front", None)) or True,
    )
    try:
        server.start()
        assert desktop_window.send_desktop_window_command(
            control_file,
            url="http://127.0.0.1:18765/#settings",
        ) is True
        deadline = time.time() + 1
        while len(actions) < 3 and time.time() < deadline:
            time.sleep(0.01)
        assert actions == [
            ("load_url", "http://127.0.0.1:18765/#settings"),
            ("restore", None),
            ("show", None),
            ("bring_to_front", None),
        ]
    finally:
        server.stop()
    assert control_file.exists() is False


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
    tray._desktop_window_control_file = Path("desktop-control.json")
    opened: list[str] = []
    commands: list[tuple[Path, str]] = []
    foreground_grants: list[int] = []
    call_order: list[str] = []
    monkeypatch.setattr(
        tray_app,
        "open_desktop_window",
        lambda url: opened.append(url),
    )
    monkeypatch.setattr(
        tray_app,
        "send_desktop_window_command",
        lambda path, *, url: (
            call_order.append("command"),
            commands.append((path, url)),
            True,
        )[-1],
    )
    monkeypatch.setattr(
        tray_app,
        "grant_desktop_window_foreground_permission",
        lambda pid: (
            call_order.append("grant"),
            foreground_grants.append(pid),
            True,
        )[-1],
    )

    result = tray._open_desktop_window("http://127.0.0.1:8000/#settings")

    assert result.mode == "webview"
    assert result.pid == 9001
    assert result.message == "已恢复并置前桌面窗口。"
    assert foreground_grants == [9001]
    assert call_order == ["grant", "command"]
    assert commands == [(Path("desktop-control.json"), "http://127.0.0.1:8000/#settings")]
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
    tray._desktop_window_control_file = Path("old-control.json")
    new_process = NewProcess()

    def fake_open(url):
        return desktop_window.DesktopWindowLaunchResult(
            opened=True,
            mode="webview",
            url=url,
            pid=new_process.pid,
            process=new_process,
            control_file=Path("new-control.json"),
        )

    monkeypatch.setattr(tray_app, "open_desktop_window", fake_open)

    result = tray._open_desktop_window("http://127.0.0.1:8000/#activity")

    assert result.mode == "webview"
    assert result.pid == 9002
    assert tray._desktop_window_process is new_process
    assert tray._desktop_window_control_file == Path("new-control.json")


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
    tray._desktop_window_control_file = Path("desktop-control.json")
    monkeypatch.setattr(tray_app, "_kill_process_tree", lambda pid: killed.append(pid))

    tray._stop_desktop_window()

    assert killed == [9001]
    assert waited == [5]
    assert tray._desktop_window_process is None
    assert tray._desktop_window_control_file is None


def test_tray_stop_cleans_up_children_before_stopping_icon() -> None:
    tray = object.__new__(tray_app.LarkSyncTray)
    events: list[str] = []

    class FakeIcon:
        def stop(self) -> None:
            events.append("icon")

    tray._running = True
    tray._icon = FakeIcon()
    tray._cleanup_all = lambda: events.append("cleanup")

    tray.stop()

    assert tray._running is False
    assert events == ["cleanup", "icon"]


def test_clean_macos_desktop_window_exit_stops_parent_app(tmp_path: Path) -> None:
    tray = object.__new__(tray_app.LarkSyncTray)
    control_file = tmp_path / "desktop-control.json"
    control_file.write_text("{}", encoding="utf-8")
    stopped: list[bool] = []

    class CleanExitProcess:
        def wait(self):
            return 0

    process = CleanExitProcess()
    tray._running = True
    tray._desktop_window_process = process
    tray._desktop_window_control_file = control_file
    tray.stop = lambda: stopped.append(True)

    tray._monitor_desktop_window_exit(process)

    assert tray._desktop_window_process is None
    assert tray._desktop_window_control_file is None
    assert control_file.exists() is False
    assert stopped == [True]


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


def test_duplicate_tray_launch_activates_existing_desktop_window(monkeypatch) -> None:
    activated: list[str] = []
    opened: list[str] = []
    browser_opened: list[str] = []

    monkeypatch.setattr(tray_app.sys, "argv", ["tray_app.py"])
    monkeypatch.setattr(tray_app, "_acquire_lock", lambda: False)
    monkeypatch.setattr(tray_app, "_configure_macos_tray_activation_policy", lambda: True)
    monkeypatch.setattr(tray_app, "get_dashboard_url", lambda: "http://127.0.0.1:8000/")
    monkeypatch.setattr(
        tray_app,
        "_activate_running_desktop_window",
        lambda url: activated.append(url) or True,
    )
    monkeypatch.setattr(tray_app, "open_desktop_window", lambda url: opened.append(url))
    monkeypatch.setattr(tray_app.webbrowser, "open", lambda url: browser_opened.append(url))

    tray_app.main()

    assert activated == ["http://127.0.0.1:8000/"]
    assert opened == []
    assert browser_opened == []


def test_desktop_window_control_file_is_shared_per_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(desktop_window, "data_dir", lambda: tmp_path)

    assert desktop_window.desktop_window_control_file() == (
        tmp_path / "runtime" / "desktop-window-control.json"
    )
    assert desktop_window._new_control_file() == desktop_window.desktop_window_control_file()
