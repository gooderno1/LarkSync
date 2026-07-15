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
