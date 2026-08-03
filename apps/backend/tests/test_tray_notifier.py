import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import notifier


class _Completed:
    returncode = 0


def test_macos_fallback_uses_native_osascript(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        notifier.subprocess if hasattr(notifier, "subprocess") else __import__("subprocess"),
        "run",
        lambda command, **kwargs: calls.append(command) or _Completed(),
    )

    assert notifier._fallback_notify('LarkSync "状态"', "同步\n完成") is True
    assert calls[0][0] == "/usr/bin/osascript"
    assert '\\"状态\\"' in calls[0][2]
    assert "同步 完成" in calls[0][2]
