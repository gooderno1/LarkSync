import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import build_installer as bi


def _mismatched_site_packages_path() -> str:
    current = f"{sys.version_info.major}{sys.version_info.minor}"
    other = "312" if current != "312" else "311"
    return fr"F:\File\Linux\Python{other}\site-packages"


def test_sanitize_pythonpath_filters_mismatched_site_packages() -> None:
    raw = os.pathsep.join([_mismatched_site_packages_path(), r"C:\repo\apps\backend"])

    sanitized, changed = bi._sanitize_pythonpath(raw)

    assert changed is True
    assert sanitized == r"C:\repo\apps\backend"


def test_sanitize_pythonpath_returns_none_when_all_entries_filtered() -> None:
    raw = _mismatched_site_packages_path()

    sanitized, changed = bi._sanitize_pythonpath(raw)

    assert changed is True
    assert sanitized is None


def test_build_subprocess_env_removes_invalid_pythonpath() -> None:
    env = bi._build_subprocess_env(
        {
            "PYTHONPATH": _mismatched_site_packages_path(),
            "LARKSYNC_PROJECT_ROOT": r"C:\repo\LarkSync",
        }
    )

    assert "PYTHONPATH" not in env
    assert env["LARKSYNC_PROJECT_ROOT"] == r"C:\repo\LarkSync"


def test_resolve_entry_script_prefers_tracked_launcher(tmp_path: Path) -> None:
    tracked = tmp_path / "apps" / "tray" / "launcher.py"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("print('ok')", encoding="utf-8")
    legacy = tmp_path / "LarkSync.pyw"
    legacy.write_text("print('legacy')", encoding="utf-8")

    resolved = bi._resolve_entry_script(tmp_path)

    assert resolved == tracked


def test_resolve_entry_script_falls_back_to_legacy(tmp_path: Path) -> None:
    legacy = tmp_path / "LarkSync.pyw"
    legacy.write_text("print('legacy')", encoding="utf-8")

    resolved = bi._resolve_entry_script(tmp_path)

    assert resolved == legacy


def test_resolve_entry_script_raises_when_missing(tmp_path: Path) -> None:
    try:
        bi._resolve_entry_script(tmp_path)
    except FileNotFoundError as exc:
        assert "launcher.py" in str(exc)
        assert "LarkSync.pyw" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
