import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import build_installer as bi


def _mismatched_site_packages_path() -> str:
    current = f"{sys.version_info.major}{sys.version_info.minor}"
    other = "312" if current != "312" else "311"
    if sys.platform == "win32":
        return fr"F:\File\Linux\Python{other}\site-packages"
    return f"/opt/python{other}/site-packages"


def _repo_backend_path() -> str:
    if sys.platform == "win32":
        return r"C:\repo\apps\backend"
    return "/repo/apps/backend"


def test_sanitize_pythonpath_filters_mismatched_site_packages() -> None:
    raw = os.pathsep.join([_mismatched_site_packages_path(), _repo_backend_path()])

    sanitized, changed = bi._sanitize_pythonpath(raw)

    assert changed is True
    assert sanitized == _repo_backend_path()


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


def test_validate_supported_build_python_accepts_baseline_version() -> None:
    bi._validate_supported_build_python((3, 14, 2))


def test_validate_supported_build_python_rejects_unsupported_version(monkeypatch) -> None:
    monkeypatch.delenv("LARKSYNC_ALLOW_UNSUPPORTED_BUILD_PYTHON", raising=False)

    with pytest.raises(RuntimeError, match="Python 3.14"):
        bi._validate_supported_build_python((3, 9, 13))


def test_validate_supported_build_python_allows_override(monkeypatch) -> None:
    monkeypatch.setenv("LARKSYNC_ALLOW_UNSUPPORTED_BUILD_PYTHON", "1")

    bi._validate_supported_build_python((3, 9, 13))


def test_collect_build_environment_summary_includes_runtime_details(monkeypatch) -> None:
    monkeypatch.setattr(bi, "_read_command_version", lambda cmd: "v25.2.1" if cmd == ["node", "--version"] else None)

    summary = bi._collect_build_environment_summary((3, 14, 2), python_executable=r"C:\Python314\python.exe")

    assert summary["python_version"] == "3.14.2"
    assert summary["python_executable"] == r"C:\Python314\python.exe"
    assert summary["node_version"] == "v25.2.1"
    assert summary["python_baseline"] == bi.BUILD_BASELINE_PYTHON_LABEL
    assert summary["node_baseline"] == bi.BUILD_BASELINE_NODE_LABEL


def test_validate_supported_build_node_accepts_baseline_version() -> None:
    bi._validate_supported_build_node("v25.2.1")


def test_validate_supported_build_node_rejects_unsupported_version(monkeypatch) -> None:
    monkeypatch.delenv("LARKSYNC_ALLOW_UNSUPPORTED_BUILD_NODE", raising=False)

    with pytest.raises(RuntimeError, match="Node 25"):
        bi._validate_supported_build_node("v20.12.0")


def test_default_macos_target_arch_uses_runner_machine(monkeypatch) -> None:
    monkeypatch.setattr(bi.sys, "platform", "darwin")

    assert bi._default_macos_target_arch("arm64") == "arm64"
    assert bi._default_macos_target_arch("aarch64") == "arm64"
    assert bi._default_macos_target_arch("x86_64") == "x86_64"
    assert bi._default_macos_target_arch("AMD64") == "x86_64"


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


def test_pyinstaller_hook_paths_points_to_repo_hook_dir(tmp_path: Path) -> None:
    paths = bi._pyinstaller_hook_paths(tmp_path)

    assert paths == [str(tmp_path / "scripts" / "pyinstaller_hooks")]


def _load_hook_module(module_name: str, hook_filename: str) -> object:
    hook_path = PROJECT_ROOT / "scripts" / "pyinstaller_hooks" / hook_filename
    spec = importlib.util.spec_from_file_location(module_name, hook_path)
    assert spec is not None and spec.loader is not None

    fake_hook_module = types.ModuleType("PyInstaller.utils.hooks")
    fake_hook_module.collect_submodules = lambda package, filter=None: [  # type: ignore[attr-defined]
        name
        for name in ("pydantic.main", "pydantic.v1", "pydantic.v1.fields")
        if filter is None or filter(name)
    ]
    monkeypatched_modules = {
        "PyInstaller": types.ModuleType("PyInstaller"),
        "PyInstaller.utils": types.ModuleType("PyInstaller.utils"),
        "PyInstaller.utils.hooks": fake_hook_module,
    }
    previous_modules = {name: sys.modules.get(name) for name in monkeypatched_modules}
    sys.modules.update(monkeypatched_modules)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


def test_custom_pydantic_hook_excludes_v1_namespace() -> None:
    module = _load_hook_module("larksync_hook_pydantic", "hook-pydantic.py")

    hiddenimports = getattr(module, "hiddenimports")
    excludedimports = getattr(module, "excludedimports")
    assert "pydantic.v1" not in hiddenimports
    assert all(not name.startswith("pydantic.v1.") for name in hiddenimports)
    assert excludedimports == ["pydantic.v1"]


def test_custom_fastapi_compat_hook_excludes_pydantic_v1() -> None:
    module = _load_hook_module("larksync_hook_fastapi_compat", "hook-fastapi._compat.shared.py")

    assert getattr(module, "excludedimports") == ["pydantic.v1"]


def test_build_dmg_uses_root_app_bundle_when_present(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    dist_dir = project_root / "dist"
    app_bundle = dist_dir / "LarkSync.app"
    script_path = project_root / "scripts" / "installer" / "macos" / "create_dmg.sh"
    app_bundle.mkdir(parents=True, exist_ok=True)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(bi, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(bi, "OUTPUT_DIR", dist_dir)
    monkeypatch.setattr(bi, "run", lambda cmd, cwd=None, env=None: captured.update({"cmd": cmd, "cwd": cwd, "env": env}))
    monkeypatch.setattr(bi, "_read_version", lambda: "v9.9.9")
    monkeypatch.setattr(bi.os, "environ", {"BASE": "1"})
    captured: dict[str, object] = {}

    bi._build_dmg()

    assert captured["cmd"] == ["bash", str(script_path)]
    assert captured["cwd"] == project_root
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["APP_VERSION"] == "v9.9.9"
    assert env["APP_BUNDLE"] == str(app_bundle)
    assert env["BASE"] == "1"


def test_build_dmg_passes_arch_suffix_when_configured(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    dist_dir = project_root / "dist"
    app_bundle = dist_dir / "LarkSync.app"
    script_path = project_root / "scripts" / "installer" / "macos" / "create_dmg.sh"
    app_bundle.mkdir(parents=True, exist_ok=True)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(bi, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(bi, "OUTPUT_DIR", dist_dir)
    monkeypatch.setattr(bi, "run", lambda cmd, cwd=None, env=None: captured.update({"cmd": cmd, "cwd": cwd, "env": env}))
    monkeypatch.setattr(bi, "_read_version", lambda: "v1.2.3")
    monkeypatch.setenv("LARKSYNC_MACOS_DMG_SUFFIX", "arm64")
    captured: dict[str, object] = {}

    bi._build_dmg()

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["APP_ARCH_SUFFIX"] == "arm64"


def test_build_dmg_falls_back_to_nested_app_bundle(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    dist_dir = project_root / "dist"
    app_bundle = dist_dir / "LarkSync" / "LarkSync.app"
    script_path = project_root / "scripts" / "installer" / "macos" / "create_dmg.sh"
    app_bundle.mkdir(parents=True, exist_ok=True)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(bi, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(bi, "OUTPUT_DIR", dist_dir)
    monkeypatch.setattr(bi, "run", lambda cmd, cwd=None, env=None: captured.update({"cmd": cmd, "cwd": cwd, "env": env}))
    monkeypatch.setattr(bi, "_read_version", lambda: "v1.2.3")
    captured: dict[str, object] = {}

    bi._build_dmg()

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["APP_BUNDLE"] == str(app_bundle)


def test_build_dmg_exits_when_app_bundle_missing(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    dist_dir = project_root / "dist"
    script_path = project_root / "scripts" / "installer" / "macos" / "create_dmg.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(bi, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(bi, "OUTPUT_DIR", dist_dir)

    with pytest.raises(SystemExit):
        bi._build_dmg()


def test_generate_spec_includes_required_hiddenimports_and_filtered_datas(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "repo"
    tracked_launcher = project_root / "apps" / "tray" / "launcher.py"
    backend_pyproject = project_root / "apps" / "backend" / "pyproject.toml"
    spec_file = project_root / "scripts" / "larksync.spec"
    tracked_launcher.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_launcher.write_text("print('ok')\n", encoding="utf-8")
    backend_pyproject.write_text('version = "v1.0.0"\n', encoding="utf-8")

    monkeypatch.setattr(bi, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(bi, "DIST_DIR", project_root / "apps" / "frontend" / "dist")
    monkeypatch.setattr(bi, "TRAY_DIR", project_root / "apps" / "tray")
    monkeypatch.setattr(bi, "BRANDING_DIR", project_root / "assets" / "branding")
    monkeypatch.setattr(bi, "BACKEND_DIR", project_root / "apps" / "backend")
    monkeypatch.setattr(bi, "SPEC_FILE", spec_file)
    monkeypatch.setattr(bi, "WINDOWS_ICON", project_root / "assets" / "branding" / "LarkSync.ico")

    bi._generate_spec()

    content = spec_file.read_text(encoding="utf-8")
    assert "'plyer'" in content
    assert "'keyring'" in content
    assert "'sqlalchemy.ext.asyncio'" in content
    assert "'sqlalchemy.dialects.sqlite'" in content
    assert "'greenlet'" in content
    assert "('"+backend_pyproject.as_posix()+"', 'apps/backend')" in content
    assert "LARKSYNC_MACOS_TARGET_ARCH" in content
    assert "platform.machine()" in content
    assert "'arm64'" in content
    assert "'x86_64'" in content
    assert "\n        ,\n" not in content


def test_backend_runtime_metadata_declares_greenlet_dependency() -> None:
    requirements = (PROJECT_ROOT / "apps" / "backend" / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "apps" / "backend" / "pyproject.toml").read_text(encoding="utf-8")

    assert "greenlet>=3.0" in requirements
    assert '"greenlet>=3.0"' in pyproject
