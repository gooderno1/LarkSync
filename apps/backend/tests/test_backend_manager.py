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


def _setup_manager(monkeypatch, frozen: bool):
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
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


def test_backend_manager_frozen_uses_backend_flag(monkeypatch):
    manager, captured = _setup_manager(monkeypatch, frozen=True)

    assert manager.start(wait=True)
    assert captured["args"] == [sys.executable, "--backend"]


def test_backend_manager_dev_uses_uvicorn_module(monkeypatch):
    manager, captured = _setup_manager(monkeypatch, frozen=False)

    assert manager.start(wait=True)
    cmd = captured["args"]
    assert cmd[:3] == [bm.PYTHON_EXE, "-m", "uvicorn"]
    assert "src.main:app" in cmd


def test_backend_manager_sanitizes_incompatible_pythonpath(monkeypatch):
    manager, captured = _setup_manager(monkeypatch, frozen=False)
    monkeypatch.setenv("PYTHONPATH", r"F:\File\Linux\Python312\site-packages;C:\repo\apps\backend")

    assert manager.start(wait=True)

    env = captured["env"]
    assert env is not None
    assert env["PYTHONPATH"] == r"C:\repo\apps\backend"
