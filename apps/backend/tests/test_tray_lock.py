from pathlib import Path
import sys

# 确保从 apps/backend 目录直接执行 pytest 时可导入 apps.tray
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import tray_app


class _DummySocket:
    def __init__(self) -> None:
        self.closed = False
        self.bind_calls: list[tuple[str, int]] = []
        self.listen_calls: list[int] = []

    def bind(self, addr: tuple[str, int]) -> None:
        self.bind_calls.append(addr)

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)

    def close(self) -> None:
        self.closed = True


def test_acquire_lock_keeps_global_socket(monkeypatch) -> None:
    dummy = _DummySocket()
    monkeypatch.setattr(tray_app.socket, "socket", lambda *_args, **_kwargs: dummy)
    tray_app._LOCK_SOCKET = None

    assert tray_app._acquire_lock() is True
    assert tray_app._LOCK_SOCKET is dummy
    assert dummy.bind_calls == [("127.0.0.1", 48901)]


def test_release_lock_closes_socket(monkeypatch) -> None:
    dummy = _DummySocket()
    tray_app._LOCK_SOCKET = dummy

    tray_app._release_lock()

    assert dummy.closed is True
    assert tray_app._LOCK_SOCKET is None

