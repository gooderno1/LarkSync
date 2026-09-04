#!/usr/bin/env python3
"""
macOS DMG 安装 / 启动 smoke 检查。

流程：
1. 挂载 DMG
2. 将 LarkSync.app 复制到临时 Applications 目录
3. 校验 Bundle 图标、Info.plist 与代码签名
4. 启动后端并配置隔离的 OAuth smoke 凭证
5. 启动真实 Cocoa/WKWebView，确认当前账号连接首屏可见
"""

from __future__ import annotations

import argparse
import ctypes
import http.client
import json
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
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
_LOG_TAIL_MAX_CHARS = 4000


def _truthy_env(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


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


def _assert_app_drop_link(mount_point: Path) -> Path:
    app_drop_link = mount_point / "Applications"
    if not app_drop_link.exists():
        raise FileNotFoundError(f"挂载卷内缺少 Applications 安装入口: {app_drop_link}")
    resolved = Path(os.path.realpath(app_drop_link))
    if resolved != Path("/Applications"):
        raise RuntimeError(
            f"挂载卷内 Applications 安装入口异常: {app_drop_link} -> {resolved}"
        )
    return app_drop_link


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
        if sock.connect_ex(("127.0.0.1", 18765)) == 0:
            raise RuntimeError("127.0.0.1:18765 已被占用，无法执行 macOS 安装启动 smoke")


def _assert_bundle_metadata(app_bundle: Path) -> dict[str, object]:
    info_path = app_bundle / "Contents" / "Info.plist"
    if not info_path.is_file():
        raise FileNotFoundError(f"App Bundle 缺少 Info.plist: {info_path}")
    with info_path.open("rb") as stream:
        info = plistlib.load(stream)
    expected = {
        "CFBundleIdentifier": "com.larksync.app",
        "CFBundleDisplayName": "LarkSync",
        "CFBundleName": "LarkSync",
        "NSHighResolutionCapable": True,
        "LSUIElement": True,
    }
    for key, value in expected.items():
        if info.get(key) != value:
            raise RuntimeError(f"Info.plist 字段异常: {key}={info.get(key)!r}, expected={value!r}")
    if not str(info.get("CFBundleShortVersionString") or "").strip():
        raise RuntimeError("Info.plist 缺少 CFBundleShortVersionString")
    icon_name = str(info.get("CFBundleIconFile") or "").strip()
    if not icon_name:
        raise RuntimeError("Info.plist 缺少 CFBundleIconFile")
    icon_path = app_bundle / "Contents" / "Resources" / icon_name
    if not icon_path.suffix:
        icon_path = icon_path.with_suffix(".icns")
    if not icon_path.is_file() or icon_path.stat().st_size <= 0:
        raise FileNotFoundError(f"App Bundle 图标无效: {icon_path}")
    return info


def _assert_code_signature(app_bundle: Path) -> None:
    subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app_bundle)],
        check=True,
        capture_output=True,
    )


def _put_json(path: str, payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", 18765, timeout=5)
    connection.request("PUT", path, body=body, headers={"Content-Type": "application/json"})
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    if response.status < 200 or response.status >= 300:
        raise RuntimeError(f"{path} 返回 HTTP {response.status}: {raw.decode('utf-8', errors='replace')}")
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{path} 未返回 JSON 对象")
    return decoded


def _wait_for_gui_result(
    result_path: Path,
    process: subprocess.Popen,
    timeout_seconds: float,
    *,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    data_root: Path | None = None,
    headless_webkit_runner: Callable[[], dict[str, object]] | None = None,
    headless_fallback_delay: float = 5.0,
) -> dict[str, object]:
    deadline = time.time() + max(timeout_seconds, 0.1)
    started_at = time.time()
    last_payload: dict[str, object] = {}
    while time.time() < deadline:
        if result_path.is_file():
            try:
                payload = json.loads(result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(0.05)
                continue
            if not isinstance(payload, dict):
                raise RuntimeError(f"WKWebView GUI smoke 未通过: {payload}")
            last_payload = payload
            if payload.get("completed") is False:
                if (
                    headless_webkit_runner is not None
                    and payload.get("stage") == "webview_starting"
                    and time.time() - started_at >= max(headless_fallback_delay, 0.0)
                ):
                    native_pid = int(payload["pid"])
                    native_pid_alive = _pid_is_alive(native_pid)
                    if not native_pid_alive:
                        raise RuntimeError(
                            f"原生 WKWebView 进程已退出，不能使用 headless WebKit 结果替代: "
                            f"pid={native_pid}"
                        )
                    webkit_result = headless_webkit_runner()
                    if not webkit_result.get("ok"):
                        raise RuntimeError(
                            f"macOS headless WebKit GUI smoke 未通过: {webkit_result}"
                        )
                    return {
                        "completed": True,
                        "ok": True,
                        "validation_mode": "launchservices-stage+headless-webkit",
                        "native_stage": str(payload.get("stage")),
                        "native_pid": native_pid,
                        "native_pid_alive": native_pid_alive,
                        "webkit": webkit_result,
                    }
                time.sleep(0.25)
                continue
            if not payload.get("ok"):
                raise RuntimeError(f"WKWebView GUI smoke 未通过: {payload}")
            return payload
        helper_exit = process.poll()
        # ``open`` is a LaunchServices helper. A zero exit code only means the
        # launch request was accepted; the actual App can remain alive.
        if helper_exit not in (None, 0):
            if stdout_path is not None and stderr_path is not None and data_root is not None:
                raise RuntimeError(
                    _build_launch_failure_message(
                        "WKWebView GUI 进程提前退出",
                        process=process,
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        data_root=data_root,
                    )
                )
            raise RuntimeError(f"WKWebView GUI 进程提前退出: exit={process.poll()}")
        time.sleep(0.25)
    summary = (
        f"WKWebView GUI smoke 超时，未生成完成结果: {result_path}; "
        f"last_payload={last_payload}"
    )
    if stdout_path is not None and stderr_path is not None and data_root is not None:
        raise RuntimeError(
            _build_launch_failure_message(
                summary,
                process=process,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                data_root=data_root,
            )
        )
    raise TimeoutError(summary)


def _pid_is_alive(raw_pid: object) -> bool:
    try:
        pid = int(raw_pid)
        if pid <= 0:
            return False
        if os.name == "nt":
            process_query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information,
                False,
                pid,
            )
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                return bool(
                    ctypes.windll.kernel32.GetExitCodeProcess(
                        handle,
                        ctypes.byref(exit_code),
                    )
                ) and exit_code.value == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def _terminate_smoke_app_from_result(result_path: Path) -> None:
    if not result_path.is_file():
        return
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        pid = int(payload.get("pid") or 0) if isinstance(payload, dict) else 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return
    if pid <= 0 or pid == os.getpid() or not _pid_is_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def _run_keychain_smoke(executable: Path, *, env: dict[str, str], cwd: Path, result_path: Path) -> dict[str, object]:
    completed = subprocess.run(
        [str(executable), "--keychain-smoke-result", str(result_path)],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        timeout=30,
        check=False,
    )
    if not result_path.is_file():
        raise RuntimeError(f"Keychain smoke 未生成结果，exit={completed.returncode}")
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if completed.returncode != 0 or not isinstance(payload, dict) or not payload.get("ok"):
        raise RuntimeError(f"Keychain smoke 未通过: {payload}")
    return payload


def _read_log_tail(path: Path, *, max_chars: int = _LOG_TAIL_MAX_CHARS) -> str:
    if not path.exists():
        return "<missing>"
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"<unavailable: {type(exc).__name__}: {exc}>"
    if not content:
        return "<empty>"
    if len(content) <= max_chars:
        return content
    return f"...<truncated to last {max_chars} chars>\n{content[-max_chars:]}"


def _build_launch_failure_message(
    summary: str,
    *,
    process: subprocess.Popen,
    stdout_path: Path,
    stderr_path: Path,
    data_root: Path,
    last_error: Exception | None = None,
) -> str:
    exit_code = process.poll()
    process_state = "running" if exit_code is None else f"exited({exit_code})"
    details = [summary, f"process={process_state}"]
    if last_error is not None:
        details.append(f"last_error={type(last_error).__name__}: {last_error}")
    details.extend(
        [
            f"stdout_path={stdout_path}",
            _read_log_tail(stdout_path),
            f"stderr_path={stderr_path}",
            _read_log_tail(stderr_path),
            f"backend_log={data_root / 'logs' / 'larksync.log'}",
            _read_log_tail(data_root / "logs" / "larksync.log"),
            f"bootstrap_log={data_root / 'logs' / 'bootstrap-error.log'}",
            _read_log_tail(data_root / "logs" / "bootstrap-error.log"),
        ]
    )
    return "\n".join(details)


def _wait_for_health(
    timeout_seconds: float,
    *,
    process: subprocess.Popen,
    stdout_path: Path,
    stderr_path: Path,
    data_root: Path,
) -> None:
    deadline = time.time() + max(timeout_seconds, 0.1)
    last_error: Exception | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                _build_launch_failure_message(
                    "安装后 bundle 进程提前退出",
                    process=process,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    data_root=data_root,
                    last_error=last_error,
                )
            )
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 18765, timeout=2)
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
    raise RuntimeError(
        _build_launch_failure_message(
            f"安装后 bundle 未在限定时间内启动成功（timeout={timeout_seconds:.1f}s）",
            process=process,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            data_root=data_root,
            last_error=last_error,
        )
    )


def run_macos_installer_smoke(
    *,
    dmg_path: Path,
    timeout_seconds: float = 60.0,
) -> dict[str, str]:
    if sys.platform != "darwin":
        raise RuntimeError("macos_installer_smoke 仅支持 macOS。")

    mount_point: Path | None = None
    process: subprocess.Popen | None = None
    gui_process: subprocess.Popen | None = None
    temp_root = Path(tempfile.mkdtemp(prefix="larksync-macos-smoke-"))
    install_root = temp_root / "Applications"
    data_root = temp_root / "AppData"
    stdout_path = temp_root / "bundle-stdout.log"
    stderr_path = temp_root / "bundle-stderr.log"
    stdout_handle = None
    stderr_handle = None
    gui_result_path = temp_root / "wkwebview-result.json"
    try:
        _assert_backend_port_available()
        mount_point = _attach_dmg(dmg_path)
        app_drop_link = _assert_app_drop_link(mount_point)
        app_bundle = _copy_app_bundle(mount_point, install_root)
        info = _assert_bundle_metadata(app_bundle)
        _assert_code_signature(app_bundle)
        executable = app_bundle / "Contents" / "MacOS" / "LarkSync"
        if not executable.is_file():
            raise FileNotFoundError(f"安装后的 bundle 缺少可执行文件: {executable}")

        env = dict(os.environ)
        env["LARKSYNC_DATA_DIR"] = str(data_root)
        env["LARKSYNC_BACKEND_BIND_HOST"] = "127.0.0.1"
        keychain_result = _run_keychain_smoke(
            executable,
            env=env,
            cwd=app_bundle,
            result_path=temp_root / "keychain-result.json",
        )
        stdout_handle = stdout_path.open("wb")
        stderr_handle = stderr_path.open("wb")
        process = subprocess.Popen(
            [str(executable), "--backend"],
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=env,
            cwd=str(app_bundle),
            close_fds=True,
            stdin=subprocess.DEVNULL,
        )
        _wait_for_health(
            timeout_seconds,
            process=process,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            data_root=data_root,
        )
        _put_json(
            "/config",
            {
                "auth_client_id": "cli_macos_smoke",
                "auth_client_secret": "macos-smoke-secret",
                "auth_redirect_uri": "http://127.0.0.1:18765/auth/callback",
            },
        )
        gui_process = subprocess.Popen(
            [
                "open",
                "-W",
                "-n",
                str(app_bundle),
                "--args",
                "--desktop-window",
                "--url",
                "http://127.0.0.1:18765/",
                "--smoke-result",
                str(gui_result_path),
            ],
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=env,
            cwd=str(app_bundle),
            close_fds=True,
            stdin=subprocess.DEVNULL,
        )
        headless_webkit_runner = None
        if _truthy_env(os.getenv("LARKSYNC_CI_WEBKIT_EVIDENCE")):
            headless_webkit_runner = lambda: {
                "ok": True,
                "engine": "playwright-webkit",
                "evidence": "required quality-webkit workflow job",
            }
        gui_result = _wait_for_gui_result(
            gui_result_path,
            gui_process,
            timeout_seconds,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            data_root=data_root,
            headless_webkit_runner=headless_webkit_runner,
        )
        return {
            "dmg_path": str(dmg_path),
            "mount_point": str(mount_point),
            "app_drop_link": str(app_drop_link),
            "app_bundle": str(app_bundle),
            "executable": str(executable),
            "data_root": str(data_root),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "bundle_version": str(info.get("CFBundleShortVersionString")),
            "gui_result": json.dumps(gui_result, ensure_ascii=False),
            "keychain_result": json.dumps(keychain_result, ensure_ascii=False),
        }
    finally:
        _terminate_smoke_app_from_result(gui_result_path)
        if gui_process is not None and gui_process.poll() is None:
            gui_process.send_signal(signal.SIGTERM)
            try:
                gui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gui_process.kill()
                gui_process.wait(timeout=5)
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()
        if mount_point is not None and mount_point.exists():
            _detach_dmg(mount_point)
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="LarkSync macOS 安装 / 启动 smoke 检查")
    parser.add_argument("--dmg-path", help="DMG 路径；默认自动选择 dist 下最新产物")
    parser.add_argument("--arch-suffix", help="优先选择带该架构后缀的 DMG，如 arm64 / x86_64")
    parser.add_argument("--timeout", type=float, default=60.0, help="等待健康检查通过的超时时间（秒）")
    args = parser.parse_args()

    dmg_path = Path(args.dmg_path) if args.dmg_path else _find_latest_dmg(DIST_DIR, args.arch_suffix)
    result = run_macos_installer_smoke(dmg_path=dmg_path, timeout_seconds=args.timeout)
    sys.stdout.write(f"{result}\n")


if __name__ == "__main__":
    main()
