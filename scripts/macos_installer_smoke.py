#!/usr/bin/env python3
"""
macOS DMG 安装 / 启动 smoke 检查。

流程：
1. 挂载 DMG
2. 将 LarkSync.app 复制到临时 Applications 目录
3. 启动 .app 内可执行文件的 `--backend` 模式
4. 轮询 /health，确认安装后的 bundle 可真实启动
"""

from __future__ import annotations

import argparse
import http.client
import os
import plistlib
import shutil
import socket
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"


def _find_latest_dmg(dist_dir: Path, suffix: str | None = None) -> Path:
    pattern = f"LarkSync-*-{suffix}.dmg" if suffix else "LarkSync-*.dmg"
    candidates = sorted(dist_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"未找到 DMG 产物: {dist_dir / pattern}")
    return candidates[0]


def _extract_mount_point(plist_bytes: bytes) -> Path:
    payload = plistlib.loads(plist_bytes)
    entities = payload.get("system-entities") or []
    for entity in entities:
        mount_point = entity.get("mount-point")
        if mount_point:
            return Path(str(mount_point))
    raise RuntimeError("未从 hdiutil 输出中解析到 mount-point")


def _attach_dmg(dmg_path: Path) -> Path:
    result = subprocess.run(
        ["hdiutil", "attach", str(dmg_path), "-nobrowse", "-plist"],
        check=True,
        capture_output=True,
    )
    return _extract_mount_point(result.stdout)


def _detach_dmg(mount_point: Path) -> None:
    subprocess.run(["hdiutil", "detach", str(mount_point), "-quiet"], check=True)


def _copy_app_bundle(mount_point: Path, target_root: Path) -> Path:
    source_app = mount_point / "LarkSync.app"
    if not source_app.is_dir():
        raise FileNotFoundError(f"挂载卷内缺少 LarkSync.app: {source_app}")
    target_root.mkdir(parents=True, exist_ok=True)
    target_app = target_root / "LarkSync.app"
    if target_app.exists():
        shutil.rmtree(target_app)
    shutil.copytree(source_app, target_app, symlinks=True)
    return target_app


def _assert_backend_port_available() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        if sock.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("127.0.0.1:8000 已被占用，无法执行 macOS 安装启动 smoke")


def _wait_for_health(timeout_seconds: float) -> None:
    deadline = time.time() + max(timeout_seconds, 0.1)
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=2)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            resp.read()
            conn.close()
            if resp.status == 200:
                return
            last_error = RuntimeError(f"health 返回 HTTP {resp.status}")
        except Exception as exc:  # pragma: no cover - smoke polling
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"安装后 bundle 未在限定时间内启动成功: {last_error}")


def run_macos_installer_smoke(
    *,
    dmg_path: Path,
    timeout_seconds: float = 20.0,
) -> dict[str, str]:
    if sys.platform != "darwin":
        raise RuntimeError("macos_installer_smoke 仅支持 macOS。")

    mount_point: Path | None = None
    process: subprocess.Popen | None = None
    temp_root = Path(tempfile.mkdtemp(prefix="larksync-macos-smoke-"))
    install_root = temp_root / "Applications"
    data_root = temp_root / "AppData"
    try:
        _assert_backend_port_available()
        mount_point = _attach_dmg(dmg_path)
        app_bundle = _copy_app_bundle(mount_point, install_root)
        executable = app_bundle / "Contents" / "MacOS" / "LarkSync"
        if not executable.is_file():
            raise FileNotFoundError(f"安装后的 bundle 缺少可执行文件: {executable}")

        env = dict(os.environ)
        env["LARKSYNC_DATA_DIR"] = str(data_root)
        env["LARKSYNC_BACKEND_BIND_HOST"] = "127.0.0.1"
        process = subprocess.Popen(
            [str(executable), "--backend"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=str(app_bundle),
            close_fds=True,
        )
        _wait_for_health(timeout_seconds)
        return {
            "dmg_path": str(dmg_path),
            "mount_point": str(mount_point),
            "app_bundle": str(app_bundle),
            "executable": str(executable),
            "data_root": str(data_root),
        }
    finally:
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if mount_point is not None and mount_point.exists():
            _detach_dmg(mount_point)
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="LarkSync macOS 安装 / 启动 smoke 检查")
    parser.add_argument("--dmg-path", help="DMG 路径；默认自动选择 dist 下最新产物")
    parser.add_argument("--arch-suffix", help="优先选择带该架构后缀的 DMG，如 arm64 / x86_64")
    parser.add_argument("--timeout", type=float, default=20.0, help="等待健康检查通过的超时时间（秒）")
    args = parser.parse_args()

    dmg_path = Path(args.dmg_path) if args.dmg_path else _find_latest_dmg(DIST_DIR, args.arch_suffix)
    result = run_macos_installer_smoke(dmg_path=dmg_path, timeout_seconds=args.timeout)
    sys.stdout.write(f"{result}\n")


if __name__ == "__main__":
    main()
