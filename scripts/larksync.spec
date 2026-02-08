# -*- mode: python ; coding: utf-8 -*-
# LarkSync PyInstaller Spec File
# 说明：用于生成桌面托盘版可执行文件

from pathlib import Path
import sys

block_cipher = None
project_root = Path(__file__).resolve().parents[1]

frontend_dist = project_root / "apps" / "frontend" / "dist"
tray_icons = project_root / "apps" / "tray" / "icons"
branding_dir = project_root / "assets" / "branding"

datas = []
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "apps/frontend/dist"))
if tray_icons.is_dir():
    datas.append((str(tray_icons), "apps/tray/icons"))
if branding_dir.is_dir():
    datas.append((str(branding_dir), "assets/branding"))

a = Analysis(
    [str(project_root / "LarkSync.pyw")],
    pathex=[str(project_root), str(project_root / "apps" / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "sqlalchemy.dialects.sqlite",
        "aiosqlite",
        "httpx",
        "loguru",
        "watchdog",
        "pystray",
        "PIL",
        "plyer",
        "keyring",
    ],
    hookspath=[],
    hooksconfig={},
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
    name="LarkSync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LarkSync",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LarkSync.app",
        icon=None,
        bundle_identifier="com.larksync.app",
    )
