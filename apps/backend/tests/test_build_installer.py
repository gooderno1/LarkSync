import importlib.util
import os
import subprocess
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


def test_custom_pydantic_hook_keeps_fastapi_v1_runtime_probe() -> None:
    module = _load_hook_module("larksync_hook_pydantic", "hook-pydantic.py")

    hiddenimports = getattr(module, "hiddenimports")
    excludedimports = getattr(module, "excludedimports")
    assert "pydantic.v1" in hiddenimports
    assert "pydantic.v1.fields" in hiddenimports
    assert excludedimports == []


def test_custom_fastapi_compat_hook_keeps_pydantic_v1_probe() -> None:
    module = _load_hook_module("larksync_hook_fastapi_compat", "hook-fastapi._compat.shared.py")

    assert getattr(module, "hiddenimports") == ["pydantic.v1"]
    assert getattr(module, "excludedimports") == []


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
    def fake_run(cmd, cwd=None, env=None):
        captured.update({"cmd": cmd, "cwd": cwd, "env": env})
        (dist_dir / "LarkSync-v9.9.9.dmg").write_bytes(b"dmg")
    monkeypatch.setattr(bi, "run", fake_run)
    monkeypatch.setattr(bi, "_sign_macos_app", lambda _app: None)
    monkeypatch.setattr(bi, "_notarize_macos_dmg", lambda _dmg: False)
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
    def fake_run(cmd, cwd=None, env=None):
        captured.update({"cmd": cmd, "cwd": cwd, "env": env})
        (dist_dir / "LarkSync-v1.2.3-arm64.dmg").write_bytes(b"dmg")
    monkeypatch.setattr(bi, "run", fake_run)
    monkeypatch.setattr(bi, "_sign_macos_app", lambda _app: None)
    monkeypatch.setattr(bi, "_notarize_macos_dmg", lambda _dmg: False)
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
    def fake_run(cmd, cwd=None, env=None):
        captured.update({"cmd": cmd, "cwd": cwd, "env": env})
        (dist_dir / "LarkSync-v1.2.3.dmg").write_bytes(b"dmg")
    monkeypatch.setattr(bi, "run", fake_run)
    monkeypatch.setattr(bi, "_sign_macos_app", lambda _app: None)
    monkeypatch.setattr(bi, "_notarize_macos_dmg", lambda _dmg: False)
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


def test_macos_create_dmg_script_falls_back_to_hdiutil(tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    script_path = project_root / "scripts" / "installer" / "macos" / "create_dmg.sh"
    source_script = PROJECT_ROOT / "scripts" / "installer" / "macos" / "create_dmg.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")

    app_bundle = project_root / "dist" / "LarkSync.app"
    executable = app_bundle / "Contents" / "MacOS" / "LarkSync"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("binary", encoding="utf-8")
    pyproject = project_root / "apps" / "backend" / "pyproject.toml"
    pyproject.parent.mkdir(parents=True, exist_ok=True)
    pyproject.write_text('[project]\nversion = "v9.9.9"\n', encoding="utf-8")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    hdiutil = fake_bin / "hdiutil"
    hdiutil.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' \"$@\" > \"$FAKE_HDIUTIL_ARGS\"\n"
        "output=\"${@: -1}\"\n"
        "mkdir -p \"$(dirname \"$output\")\"\n"
        "printf 'fake-dmg' > \"$output\"\n",
        encoding="utf-8",
    )
    hdiutil.chmod(0o755)
    args_path = tmp_path / "hdiutil-args.txt"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "APP_ARCH_SUFFIX": "arm64",
        "LARKSYNC_DMG_TOOL": "hdiutil",
        "FAKE_HDIUTIL_ARGS": str(args_path),
    }
    env.pop("APP_VERSION", None)

    completed = subprocess.run(
        ["/bin/bash", str(script_path)],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    expected = project_root / "dist" / "LarkSync-v9.9.9-arm64.dmg"
    assert completed.returncode == 0, completed.stderr
    assert expected.read_bytes() == b"fake-dmg"
    hdiutil_args = args_path.read_text(encoding="utf-8")
    assert "-volname\nLarkSync\n" in hdiutil_args
    assert str(expected) in hdiutil_args
    assert f"OK: DMG created at {expected}" in completed.stdout


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
    monkeypatch.setattr(bi, "MACOS_ICON", project_root / "assets" / "branding" / "LarkSync.icns")
    monkeypatch.setattr(bi, "MACOS_ENTITLEMENTS", project_root / "scripts" / "installer" / "macos" / "LarkSync.entitlements")

    bi._generate_spec()

    content = spec_file.read_text(encoding="utf-8")
    assert "'plyer'" in content
    assert "'keyring'" in content
    assert "'webview'" in content
    assert "'webview.platforms.edgechromium'" in content
    assert "'sqlalchemy.ext.asyncio'" in content
    assert "'sqlalchemy.dialects.sqlite'" in content
    assert "'greenlet'" in content
    assert "('"+backend_pyproject.as_posix()+"', 'apps/backend')" in content
    assert "LARKSYNC_MACOS_TARGET_ARCH" in content
    assert "platform.machine()" in content
    assert "'arm64'" in content
    assert "'x86_64'" in content
    assert "LarkSync.icns" in content
    assert "CFBundleDisplayName" in content
    assert "CFBundleShortVersionString" in content
    assert "LSMinimumSystemVersion" in content
    assert "LARKSYNC_MACOS_CODESIGN_IDENTITY" in content
    assert "entitlements_file" in content
    assert "\n        ,\n" not in content


def test_backend_runtime_metadata_declares_desktop_runtime_dependencies() -> None:
    requirements = (PROJECT_ROOT / "apps" / "backend" / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "apps" / "backend" / "pyproject.toml").read_text(encoding="utf-8")

    assert "greenlet>=3.0" in requirements
    assert '"greenlet>=3.0"' in pyproject
    assert "pywebview>=5.0" in requirements
    assert '"pywebview>=5.0"' in pyproject


def test_checked_in_spec_includes_webview_hiddenimports() -> None:
    spec = (PROJECT_ROOT / "scripts" / "larksync.spec").read_text(encoding="utf-8")

    assert '"webview"' in spec
    assert '"webview.platforms.edgechromium"' in spec
    assert '"webview.platforms.winforms"' in spec
    assert 'icon=str(macos_icon)' in spec
    assert '"CFBundleDisplayName": "LarkSync"' in spec
    assert '"LSMinimumSystemVersion": "12.0"' in spec


def test_sign_macos_app_uses_hardened_runtime_for_developer_id(monkeypatch, tmp_path: Path) -> None:
    app = tmp_path / "LarkSync.app"
    app.mkdir()
    commands: list[list[str]] = []
    monkeypatch.setenv("LARKSYNC_MACOS_CODESIGN_IDENTITY", "Developer ID Application: Example")
    monkeypatch.setattr(bi, "MACOS_ENTITLEMENTS", tmp_path / "LarkSync.entitlements")
    bi.MACOS_ENTITLEMENTS.write_text("plist", encoding="utf-8")
    monkeypatch.setattr(bi, "run", lambda command, cwd=None, env=None: commands.append(command))

    bi._sign_macos_app(app)

    assert commands[0][:7] == [
        "codesign", "--force", "--deep", "--sign", "Developer ID Application: Example", "--options", "runtime"
    ]
    assert "--timestamp" in commands[0]
    assert commands[1][:5] == ["codesign", "--verify", "--deep", "--strict", "--verbose=2"]


def test_required_macos_notarization_rejects_missing_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LARKSYNC_REQUIRE_MACOS_NOTARIZATION", "1")
    monkeypatch.delenv("LARKSYNC_NOTARYTOOL_PROFILE", raising=False)
    monkeypatch.delenv("APPLE_ID", raising=False)
    monkeypatch.delenv("APPLE_TEAM_ID", raising=False)
    monkeypatch.delenv("APPLE_APP_SPECIFIC_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="要求 Apple 公证凭证"):
        bi._notarize_macos_dmg(tmp_path / "LarkSync.dmg")
