import os
import sys
from pathlib import Path

# 确保从 apps/backend 目录直接执行 pytest 时可导入 apps.tray
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import backend_manager as bm


class _DummyProcess:
    def __init__(self, args, cwd=None, creationflags=0, stdout=None, stderr=None, env=None):
        self.args = args
        self.cwd = cwd
        self.creationflags = creationflags
        self.stdout = stdout
        self.stderr = stderr
        self.env = env
        self.pid = 12345

    def poll(self):
        return None


def _setup_manager(monkeypatch, tmp_path: Path, frozen: bool):
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path / "data"))
    if frozen:
        monkeypatch.setattr(sys, "executable", r"C:\LarkSync.exe", raising=False)

    captured = {}

    def fake_popen(cmd, **kwargs):
        proc = _DummyProcess(cmd, **kwargs)
        captured["args"] = proc.args
        captured["cwd"] = proc.cwd
        captured["env"] = kwargs.get("env")
        return proc

    monkeypatch.setattr(bm.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(bm.BackendManager, "_wait_for_ready", lambda self: True)
    monkeypatch.setattr(bm.BackendManager, "_is_port_in_use", lambda self: False)

    return bm.BackendManager(), captured


def _mismatched_site_packages_path() -> str:
    if sys.platform == "win32":
        return r"F:\File\Linux\Python312\site-packages"
    return "/opt/python312/site-packages"


def _repo_backend_path() -> str:
    if sys.platform == "win32":
        return r"C:\repo\apps\backend"
    return "/repo/apps/backend"


def test_backend_manager_frozen_uses_backend_flag(monkeypatch, tmp_path: Path):
    manager, captured = _setup_manager(monkeypatch, tmp_path, frozen=True)

    assert manager.start(wait=True)
    assert captured["args"] == [sys.executable, "--backend"]


def test_backend_manager_dev_uses_uvicorn_module(monkeypatch, tmp_path: Path):
    manager, captured = _setup_manager(monkeypatch, tmp_path, frozen=False)

    assert manager.start(wait=True)
    cmd = captured["args"]
    assert cmd[:3] == [bm.PYTHON_EXE, "-m", "uvicorn"]
    assert "src.main:app" in cmd


def test_backend_manager_sanitizes_incompatible_pythonpath(monkeypatch, tmp_path: Path):
    manager, captured = _setup_manager(monkeypatch, tmp_path, frozen=False)
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([_mismatched_site_packages_path(), _repo_backend_path()]),
    )

    assert manager.start(wait=True)

    env = captured["env"]
    assert env is not None
    assert env["PYTHONPATH"] == _repo_backend_path()


def test_backend_manager_reuses_external_backend_with_same_data_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    expected_data_dir = tmp_path / "data"
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(expected_data_dir))
    manager = bm.BackendManager()

    monkeypatch.setattr(manager, "_is_port_in_use", lambda: True)
    monkeypatch.setattr(manager, "health_check", lambda: True)
    monkeypatch.setattr(
        manager,
        "_read_existing_backend_data_dir",
        lambda: expected_data_dir,
    )

    assert manager.start(wait=True) is True
    assert manager._external_backend is True


def test_backend_manager_rejects_external_backend_with_different_data_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path / "expected"))
    manager = bm.BackendManager()

    monkeypatch.setattr(manager, "_is_port_in_use", lambda: True)
    monkeypatch.setattr(manager, "health_check", lambda: True)
    monkeypatch.setattr(
        manager,
        "_read_existing_backend_data_dir",
        lambda: tmp_path / "other",
    )

    assert manager.start(wait=True) is False
    assert manager._external_backend is False


def test_runtime_data_dir_uses_external_app_data_when_frozen(
    monkeypatch,
    tmp_path: Path,
) -> None:
    external_data_dir = tmp_path / "Library" / "Application Support" / "LarkSync"
    monkeypatch.delenv("LARKSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(bm, "backend_data_dir", lambda: external_data_dir)

    assert bm._runtime_data_dir() == external_data_dir
