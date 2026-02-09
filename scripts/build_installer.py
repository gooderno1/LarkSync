#!/usr/bin/env python3
"""
LarkSync 安装包构建脚本

流程：
  1. 构建前端 (npm run build)
  2. 生成托盘图标
  3. PyInstaller 打包为独立应用
  4. (可选) 生成平台安装包 (NSIS / DMG)

使用方法：
  python scripts/build_installer.py           # 仅 PyInstaller 打包
  python scripts/build_installer.py --nsis    # Windows: 额外生成 NSIS 安装包
  python scripts/build_installer.py --dmg     # macOS: 额外生成 DMG
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "apps" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
BACKEND_DIR = PROJECT_ROOT / "apps" / "backend"
TRAY_DIR = PROJECT_ROOT / "apps" / "tray"
OUTPUT_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = PROJECT_ROOT / "scripts" / "larksync.spec"
NSIS_DIR = PROJECT_ROOT / "scripts" / "installer" / "nsis"
PYPROJECT_FILE = BACKEND_DIR / "pyproject.toml"
BRANDING_DIR = PROJECT_ROOT / "assets" / "branding"
BRAND_ICON = BRANDING_DIR / "LarkSync_Logo_Icon_FullColor.png"
WINDOWS_ICON = BRANDING_DIR / "LarkSync.ico"


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _resolve_cmd(cmd: list[str]) -> list[str]:
    if not cmd:
        return cmd
    if Path(cmd[0]).is_file():
        return cmd
    resolved = shutil.which(cmd[0])
    if not resolved and sys.platform == "win32":
        if not cmd[0].lower().endswith((".exe", ".cmd", ".bat")):
            for suffix in (".cmd", ".exe", ".bat"):
                candidate = shutil.which(f"{cmd[0]}{suffix}")
                if candidate:
                    resolved = candidate
                    break
    if resolved:
        return [resolved, *cmd[1:]]
    return cmd


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    resolved_cmd = _resolve_cmd(cmd)
    print(f"  → {' '.join(resolved_cmd)}")
    result = subprocess.run(resolved_cmd, cwd=str(cwd) if cwd else None, env=env)
    if result.returncode != 0:
        print(f"  ✗ 命令失败 (exit {result.returncode})")
        sys.exit(1)


def step_build_frontend() -> None:
    print("\n[1/4] 构建前端...")
    if not (FRONTEND_DIR / "node_modules").is_dir():
        run(["npm", "install"], cwd=FRONTEND_DIR)
    run(["npm", "run", "build"], cwd=FRONTEND_DIR)
    assert DIST_DIR.is_dir(), f"前端构建产物不存在: {DIST_DIR}"
    print("  ✓ 前端构建完成")


def step_generate_icons() -> None:
    print("\n[2/4] 生成托盘图标...")
    sys.path.insert(0, str(PROJECT_ROOT))
    from apps.tray.icon_generator import generate_icons
    icons = generate_icons(force=True)
    _ensure_windows_icon()
    print(f"  ✓ 生成了 {len(icons)} 个图标")


def step_pyinstaller() -> None:
    print("\n[3/4] PyInstaller 打包...")

    # 确保 pyinstaller 可用
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("  安装 PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 生成 spec 文件（如果不存在）
    if not SPEC_FILE.is_file():
        _generate_spec()

    # 执行打包
    env = os.environ.copy()
    env["LARKSYNC_PROJECT_ROOT"] = str(PROJECT_ROOT)
    run([
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath", str(OUTPUT_DIR),
        "--workpath", str(PROJECT_ROOT / "build"),
    ], cwd=PROJECT_ROOT, env=env)

    exe_name = "LarkSync.exe" if sys.platform == "win32" else "LarkSync"
    exe_path = OUTPUT_DIR / "LarkSync" / exe_name
    if exe_path.is_file():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ 打包完成: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"  ✓ 打包完成: {OUTPUT_DIR / 'LarkSync'}/")


def step_platform_installer(nsis: bool = False, dmg: bool = False) -> None:
    print("\n[4/4] 生成安装包...")

    if nsis and sys.platform == "win32":
        _build_nsis()
    elif dmg and sys.platform == "darwin":
        _build_dmg()
    else:
        print("  跳过（未指定平台安装包参数）")
        print("  提示：使用 --nsis (Windows) 或 --dmg (macOS) 生成安装包")


def _generate_spec() -> None:
    """生成 PyInstaller spec 文件。"""
    print("  生成 spec 文件...")

    # 收集前端 dist 文件
    frontend_datas = f"('{DIST_DIR}', 'apps/frontend/dist')" if DIST_DIR.is_dir() else ""

    # 收集托盘图标
    icons_dir = TRAY_DIR / "icons"
    icons_datas = f"('{icons_dir}', 'apps/tray/icons')" if icons_dir.is_dir() else ""

    # 收集品牌资源
    branding_datas = f"('{BRANDING_DIR}', 'assets/branding')" if BRANDING_DIR.is_dir() else ""

    # 收集 backend 版本信息
    backend_pyproject = BACKEND_DIR / "pyproject.toml"
    pyproject_datas = f"('{backend_pyproject}', 'apps/backend')" if backend_pyproject.is_file() else ""

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
# LarkSync PyInstaller Spec File
# 自动生成，可手动修改

import os
import sys
from pathlib import Path

block_cipher = None

def _resolve_project_root() -> Path:
    env_root = os.getenv('LARKSYNC_PROJECT_ROOT') or os.getenv('LARKSYNC_ROOT')
    if env_root:
        return Path(env_root).expanduser().resolve()
    try:
        return Path(__file__).resolve().parents[1]
    except NameError:
        return Path.cwd().resolve()


project_root = _resolve_project_root()

a = Analysis(
    ['{(PROJECT_ROOT / "LarkSync.pyw").as_posix()}'],
    pathex=[project_root, '{BACKEND_DIR.as_posix()}'],
    binaries=[],
    datas=[
        {frontend_datas},
        {icons_datas},
        {branding_datas},
        {pyproject_datas},
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pydantic',
        'sqlalchemy',
        'aiosqlite',
        'httpx',
        'loguru',
        'watchdog',
        'pystray',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LarkSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无终端窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{WINDOWS_ICON.as_posix()}' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LarkSync',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LarkSync.app',
        icon=None,
        bundle_identifier='com.larksync.app',
    )
"""
    SPEC_FILE.write_text(spec_content, encoding="utf-8")
    print(f"  ✓ spec 文件: {SPEC_FILE}")


def _build_nsis() -> None:
    """Windows: 使用 NSIS 生成安装包。"""
    nsis_exe = shutil.which("makensis")
    if not nsis_exe and sys.platform == "win32":
        candidates = [
            r"C:\Program Files (x86)\NSIS\makensis.exe",
            r"C:\Program Files\NSIS\makensis.exe",
        ]
        for candidate in candidates:
            if Path(candidate).is_file():
                nsis_exe = candidate
                break
    if not nsis_exe:
        print("  ✗ 未找到 makensis，请安装 NSIS：https://nsis.sourceforge.io/")
        sys.exit(1)

    nsi_script = NSIS_DIR / "larksync.nsi"
    if not nsi_script.is_file():
        print(f"  ✗ 未找到 NSIS 脚本: {nsi_script}")
        print("  提示：请参考 docs/design/v0.4.0-desktop-tray-design.md 创建 NSIS 脚本")
        return
    if not (OUTPUT_DIR / "LarkSync").is_dir():
        print("  ✗ 未找到 PyInstaller 产物，请先执行 PyInstaller 打包")
        return

    version = _read_version()
    defines = [
        f"/DAPP_VERSION={_quote_define(version)}",
    ]

    run([nsis_exe, *defines, str(nsi_script)])
    output_file = OUTPUT_DIR / f"LarkSync-Setup-{version}.exe"
    if not output_file.is_file():
        print(f"  ✗ 未生成 NSIS 安装包: {output_file}")
        sys.exit(1)
    print(f"  ✓ NSIS 安装包已生成: {output_file}")


def _build_dmg() -> None:
    """macOS: 生成 DMG 安装包。"""
    create_dmg_script = PROJECT_ROOT / "scripts" / "installer" / "macos" / "create_dmg.sh"

    if not create_dmg_script.is_file():
        print(f"  ✗ 未找到 DMG 脚本: {create_dmg_script}")
        sys.exit(1)

    candidates = [
        OUTPUT_DIR / "LarkSync.app",
        OUTPUT_DIR / "LarkSync" / "LarkSync.app",
    ]
    app_bundle = next((path for path in candidates if path.is_dir()), None)
    if not app_bundle:
        print("  ✗ 未找到 .app bundle")
        for candidate in candidates:
            print(f"    - 期待路径: {candidate}")
        sys.exit(1)

    version = _read_version()
    env = os.environ.copy()
    env["APP_VERSION"] = version
    env["APP_BUNDLE"] = str(app_bundle)
    run(["bash", str(create_dmg_script)], cwd=PROJECT_ROOT, env=env)
    print("  ✓ DMG 已生成")


def _read_version() -> str:
    env_version = os.getenv("LARKSYNC_VERSION")
    if env_version:
        return env_version
    if not PYPROJECT_FILE.is_file():
        return "0.0.0"
    try:
        content = PYPROJECT_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = PYPROJECT_FILE.read_text(encoding="utf-8-sig")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        return "0.0.0"
    return match.group(1)


def _quote_define(value: str) -> str:
    if " " in value or "\t" in value:
        return f'"{value}"'
    return value


def _ensure_windows_icon() -> None:
    """生成 Windows 使用的 .ico 图标。"""
    if WINDOWS_ICON.is_file():
        return
    if not BRAND_ICON.is_file():
        return
    try:
        from PIL import Image
    except ImportError:
        return
    img = Image.open(str(BRAND_ICON)).convert("RGBA")
    size = 256
    img = img.resize((size, size), Image.LANCZOS)
    WINDOWS_ICON.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        str(WINDOWS_ICON),
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )


def main() -> None:
    _configure_output()
    parser = argparse.ArgumentParser(description="LarkSync 安装包构建工具")
    parser.add_argument("--nsis", action="store_true", help="Windows: 生成 NSIS 安装包")
    parser.add_argument("--dmg", action="store_true", help="macOS: 生成 DMG 安装包")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端构建")
    args = parser.parse_args()

    print("=" * 50)
    print("  LarkSync 安装包构建")
    print("=" * 50)

    if not args.skip_frontend:
        step_build_frontend()
    step_generate_icons()
    step_pyinstaller()
    step_platform_installer(nsis=args.nsis, dmg=args.dmg)

    print("\n" + "=" * 50)
    print("  构建完成！")
    print(f"  产物目录: {OUTPUT_DIR / 'LarkSync'}")
    print("=" * 50)


if __name__ == "__main__":
    main()
