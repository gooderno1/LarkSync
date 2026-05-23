#!/usr/bin/env python3
"""
Windows 静默安装链路 smoke 检查工具。

默认使用一个不存在的安装包路径，验证 bootstrap / worker / handoff
是否能真实推进到 `launch_failed`，从而确认 PowerShell 脚本、编码和
接管链路都已执行。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.tray import tray_app


def _read_handoff_payload(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _append_smoke_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with log_path.open("a", encoding="utf-8", errors="ignore") as file:
        file.write(f"[{timestamp}] {message}\n")


def _wait_for_ready_handoff(
    path: Path,
    request_id: str,
    timeout: float,
    *,
    expected_stage: str,
) -> dict[str, object] | None:
    if not request_id:
        return None
    deadline = time.time() + max(timeout, 0.1)
    latest: dict[str, object] | None = None
    transient_stages = {"bootstrap_started", "helper_started"}
    while time.time() < deadline:
        payload = _read_handoff_payload(path)
        if payload and str(payload.get("request_id", "")).strip() == request_id:
            latest = payload
            stage = str(payload.get("stage") or "").strip()
            if stage == expected_stage:
                return payload
            if stage in transient_stages:
                time.sleep(0.2)
                continue
            return payload
        time.sleep(0.2)
    return latest


def run_update_install_smoke(
    *,
    installer_path: Path,
    restart_path: Path | None = None,
    expected_stage: str = "launch_failed",
    timeout_seconds: float = 20.0,
) -> dict[str, object]:
    if sys.platform != "win32":
        raise RuntimeError("update_install_smoke 仅支持 Windows。")

    request_id = f"smoke-{uuid.uuid4().hex[:12]}"
    temp_root = Path(tempfile.mkdtemp(prefix="larksync-update-smoke-"))
    handoff_path = temp_root / "install-handoff.json"
    log_path = temp_root / "update-install.log"
    script_dir = temp_root / "install-scripts"

    command = tray_app._build_windows_silent_bootstrap_command(
        installer_path,
        restart_path=restart_path,
        log_path=log_path,
        handoff_path=handoff_path,
        request_id=request_id,
        script_dir=script_dir,
    )
    process, creationflags = tray_app._launch_hidden_helper_process(
        command,
        on_fallback=lambda message: _append_smoke_log(log_path, message),
    )
    handoff = _wait_for_ready_handoff(
        handoff_path,
        request_id,
        timeout_seconds,
        expected_stage=expected_stage,
    )
    observed_stage = str((handoff or {}).get("stage") or "")
    log_tail = log_path.read_text(encoding="utf-8", errors="ignore").lstrip("\ufeff") if log_path.exists() else ""

    result = {
        "request_id": request_id,
        "pid": process.pid,
        "installer_path": str(installer_path),
        "restart_path": str(restart_path) if restart_path else None,
        "launch_creationflags": creationflags,
        "expected_stage": expected_stage,
        "observed_stage": observed_stage or None,
        "handoff": handoff,
        "handoff_path": str(handoff_path),
        "log_path": str(log_path),
        "script_dir": str(script_dir),
        "log_tail": log_tail,
        "success": observed_stage == expected_stage,
    }
    if observed_stage != expected_stage:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="LarkSync 静默安装链路 smoke 检查")
    parser.add_argument("--installer-path", help="安装包路径；默认使用不存在的路径验证链路推进")
    parser.add_argument("--restart-path", help="安装后重启路径，可选")
    parser.add_argument("--expect-stage", default="launch_failed", help="期望 handoff stage，默认 launch_failed")
    parser.add_argument("--timeout", type=float, default=20.0, help="等待 handoff 超时时间（秒）")
    args = parser.parse_args()

    installer_path = (
        Path(args.installer_path)
        if args.installer_path
        else Path(tempfile.gettempdir()) / f"LarkSync-Smoke-{uuid.uuid4().hex}.exe"
    )
    restart_path = Path(args.restart_path) if args.restart_path else None
    result = run_update_install_smoke(
        installer_path=installer_path,
        restart_path=restart_path,
        expected_stage=args.expect_stage,
        timeout_seconds=args.timeout,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
