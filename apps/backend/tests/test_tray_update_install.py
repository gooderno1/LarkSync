from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import tray_app


class _DummyBackend:
    def maybe_auto_restart(self) -> bool:
        return False


def test_tray_processes_install_request_and_stops(monkeypatch, tmp_path: Path) -> None:
    requested_path = tmp_path / "LarkSync-Setup-v0.5.51.exe"
    requested_path.write_bytes(b"exe")
    consumed: list[str] = []
    stopped: list[bool] = []

    tray = object.__new__(tray_app.LarkSyncTray)
    tray._backend = _DummyBackend()
    tray._running = True
    tray._icon = None
    tray._dev_mode = False
    tray._current_state = "idle"
    tray._global_paused = False
    tray._last_conflict_count = 0

    monkeypatch.setattr(
        tray_app,
        "_load_install_request",
        lambda: {"installer_path": str(requested_path)},
    )
    monkeypatch.setattr(tray_app, "_clear_install_request", lambda: consumed.append("cleared"))
    monkeypatch.setattr(
        tray,
        "_schedule_installer_launch",
        lambda path: consumed.append(str(path)),
    )
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(tray, "stop", lambda: stopped.append(True))

    handled = tray._handle_pending_install_request()

    assert handled is True
    assert consumed == [str(requested_path), "cleared"]
    assert stopped == [True]
