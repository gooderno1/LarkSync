from pathlib import Path
import sys
import types

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import launcher
from apps.tray import config as tray_config


def test_packaged_launcher_writes_bootstrap_error_to_isolated_data_dir(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path))

    path = launcher._write_bootstrap_error(RuntimeError("packaged boom"))

    assert path == tmp_path / "logs" / "bootstrap-error.log"
    content = path.read_text(encoding="utf-8")
    assert "RuntimeError: packaged boom" in content


def test_packaged_backend_disables_uvicorn_console_logging(
    tmp_path: Path, monkeypatch
) -> None:
    captured = {}
    fake_uvicorn = types.ModuleType("uvicorn")

    def fake_run(app, **kwargs) -> None:
        captured["app"] = app
        captured.update(kwargs)

    fake_uvicorn.run = fake_run  # type: ignore[attr-defined]
    fake_main = types.ModuleType("src.main")
    fake_main.app = object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setitem(sys.modules, "src.main", fake_main)
    monkeypatch.setattr(tray_config, "BACKEND_DIR", tmp_path)
    monkeypatch.setattr(tray_config, "BACKEND_HOST", "127.0.0.1")
    monkeypatch.setattr(tray_config, "BACKEND_PORT", 18400)
    monkeypatch.setattr(launcher, "_validate_backend_runtime", lambda: None)

    launcher._run_backend()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 18400
    assert captured["log_config"] is None
    assert captured["access_log"] is False


def test_packaged_launcher_fast_paths_desktop_window_without_tray_import(monkeypatch) -> None:
    calls: list[list[str]] = []
    fake_desktop = types.ModuleType("apps.tray.desktop_window")
    fake_desktop.main = lambda args: calls.append(args) or 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "apps.tray.desktop_window", fake_desktop)
    monkeypatch.delitem(sys.modules, "apps.tray.tray_app", raising=False)

    result = launcher.entrypoint(
        ["--desktop-window", "--url", "http://127.0.0.1:18765/", "--debug-window"]
    )

    assert result == 0
    assert calls == [["--url", "http://127.0.0.1:18765/", "--debug-window"]]
    assert "apps.tray.tray_app" not in sys.modules


def test_packaged_launcher_enables_frozen_multiprocessing_before_argument_routing(
    monkeypatch,
) -> None:
    calls: list[str] = []
    fake_desktop = types.ModuleType("apps.tray.desktop_window")
    fake_desktop.main = lambda _args: calls.append("desktop") or 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "apps.tray.desktop_window", fake_desktop)
    monkeypatch.setattr(
        launcher.multiprocessing,
        "freeze_support",
        lambda: calls.append("freeze_support"),
    )

    assert launcher.entrypoint(["--desktop-window", "--url", "http://127.0.0.1:18765/"]) == 0
    assert calls == ["freeze_support", "desktop"]


def test_packaged_launcher_keychain_smoke_round_trips_and_deletes(monkeypatch, tmp_path: Path) -> None:
    values: dict[tuple[str, str], str] = {}
    fake_keyring = types.ModuleType("keyring")
    fake_keyring.set_password = lambda service, account, value: values.__setitem__((service, account), value)  # type: ignore[attr-defined]
    fake_keyring.get_password = lambda service, account: values.get((service, account))  # type: ignore[attr-defined]
    fake_keyring.delete_password = lambda service, account: values.pop((service, account), None)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)
    result_path = tmp_path / "keychain.json"

    assert launcher.entrypoint(["--keychain-smoke-result", str(result_path)]) == 0
    assert '"ok": true' in result_path.read_text(encoding="utf-8")
    assert values == {}
