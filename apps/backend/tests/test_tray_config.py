import importlib
import sys
from pathlib import Path

# 确保从 apps/backend 目录直接执行 pytest 时可导入 apps.tray
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_tray_config(
    monkeypatch,
    *,
    platform: str,
    bind_host: str | None = None,
    client_host: str | None = None,
):
    monkeypatch.delenv("LARKSYNC_BACKEND_BIND_HOST", raising=False)
    monkeypatch.delenv("LARKSYNC_BACKEND_CLIENT_HOST", raising=False)
    if bind_host is not None:
        monkeypatch.setenv("LARKSYNC_BACKEND_BIND_HOST", bind_host)
    if client_host is not None:
        monkeypatch.setenv("LARKSYNC_BACKEND_CLIENT_HOST", client_host)

    monkeypatch.setattr(sys, "platform", platform, raising=False)
    import apps.tray.config as tray_config

    return importlib.reload(tray_config)


def test_windows_default_bind_host_supports_wsl(monkeypatch):
    cfg = _reload_tray_config(monkeypatch, platform="win32")

    assert cfg.BACKEND_HOST == "0.0.0.0"
    assert cfg.BACKEND_CLIENT_HOST == "127.0.0.1"
    assert cfg.BACKEND_URL == "http://127.0.0.1:8000"


def test_non_windows_default_bind_host_is_loopback(monkeypatch):
    cfg = _reload_tray_config(monkeypatch, platform="linux")

    assert cfg.BACKEND_HOST == "127.0.0.1"
    assert cfg.BACKEND_CLIENT_HOST == "127.0.0.1"


def test_bind_host_env_override(monkeypatch):
    cfg = _reload_tray_config(monkeypatch, platform="win32", bind_host="127.0.0.1")

    assert cfg.BACKEND_HOST == "127.0.0.1"
    assert cfg.BACKEND_CLIENT_HOST == "127.0.0.1"
    assert cfg.BACKEND_URL == "http://127.0.0.1:8000"


def test_client_host_env_override(monkeypatch):
    cfg = _reload_tray_config(
        monkeypatch,
        platform="win32",
        bind_host="0.0.0.0",
        client_host="192.168.50.9",
    )

    assert cfg.BACKEND_HOST == "0.0.0.0"
    assert cfg.BACKEND_CLIENT_HOST == "192.168.50.9"
    assert cfg.BACKEND_URL == "http://192.168.50.9:8000"
