from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


STATUS_COMMAND = "lark-cli auth status --json --verify"
LOGIN_COMMAND = "lark-cli auth login --domain docs --domain drive --no-wait --json"
QRCODE_COMMAND = 'lark-cli auth qrcode "<verification_url>" --output larksync-cli-auth.png'


class LarkCliUserStatus(BaseModel):
    available: bool = False
    verified: bool = False
    status: str | None = None
    token_status: str | None = None
    user_name: str | None = None
    open_id_present: bool = False
    scope_count: int = 0
    docs_scope_detected: bool = False
    drive_scope_detected: bool = False
    expires_at: str | None = None
    refresh_expires_at: str | None = None


class LarkCliAuthStatus(BaseModel):
    installed: bool
    executable: str | None = None
    brand: str | None = None
    identity: str | None = None
    verified: bool = False
    user: LarkCliUserStatus | None = None
    can_assist_oauth: bool = False
    message: str
    last_error: str | None = None
    status_command: str = STATUS_COMMAND
    login_command: str = LOGIN_COMMAND
    qrcode_command: str = QRCODE_COMMAND


@dataclass(frozen=True)
class LarkCliCommandResult:
    returncode: int
    stdout: str
    stderr: str


def get_lark_cli_auth_status(
    *,
    which=shutil.which,
    run=subprocess.run,
    timeout_seconds: float = 6.0,
) -> LarkCliAuthStatus:
    executable = which("lark-cli")
    if not executable:
        return LarkCliAuthStatus(
            installed=False,
            message="未检测到 lark-cli。可继续使用 LarkSync 原生 OAuth。",
        )

    try:
        result = _run_status_command(executable, run=run, timeout_seconds=timeout_seconds)
    except subprocess.TimeoutExpired:
        return LarkCliAuthStatus(
            installed=True,
            executable=_display_executable(executable),
            message="lark-cli 状态检查超时。可稍后重试或继续使用原生 OAuth。",
            last_error="timeout",
        )
    except OSError as exc:
        return LarkCliAuthStatus(
            installed=True,
            executable=_display_executable(executable),
            message="lark-cli 无法启动。可继续使用 LarkSync 原生 OAuth。",
            last_error=f"{type(exc).__name__}: {exc}",
        )

    if result.returncode != 0:
        return LarkCliAuthStatus(
            installed=True,
            executable=_display_executable(executable),
            message="lark-cli 已安装，但当前登录态不可用。",
            last_error=_short_error(result.stderr or result.stdout),
        )

    payload = _parse_json_object(result.stdout)
    if payload is None:
        return LarkCliAuthStatus(
            installed=True,
            executable=_display_executable(executable),
            message="lark-cli 已安装，但状态输出不是 JSON。",
            last_error=_short_error(result.stdout),
        )

    user = _parse_user_status(payload)
    can_assist = bool(
        user
        and user.available
        and user.verified
        and user.docs_scope_detected
        and user.drive_scope_detected
    )
    message = (
        "lark-cli 用户身份可用，可作为后续设备码授权方案的辅助状态。"
        if can_assist
        else "lark-cli 已安装，但用户身份或 docs/drive 授权仍需确认。"
    )
    return LarkCliAuthStatus(
        installed=True,
        executable=_display_executable(executable),
        brand=_get_str(payload, "brand"),
        identity=_get_str(payload, "identity"),
        verified=bool(payload.get("verified")),
        user=user,
        can_assist_oauth=can_assist,
        message=message,
    )


def _run_status_command(
    executable: str,
    *,
    run,
    timeout_seconds: float,
) -> LarkCliCommandResult:
    env = os.environ.copy()
    env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
    env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout_seconds,
        "env": env,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = run(
        [executable, "auth", "status", "--json", "--verify"],
        **kwargs,
    )
    return LarkCliCommandResult(
        returncode=int(getattr(completed, "returncode", 1)),
        stdout=str(getattr(completed, "stdout", "") or ""),
        stderr=str(getattr(completed, "stderr", "") or ""),
    )


def _parse_user_status(payload: dict[str, Any]) -> LarkCliUserStatus | None:
    identities = payload.get("identities")
    if not isinstance(identities, dict):
        return None
    user = identities.get("user")
    if not isinstance(user, dict):
        return None

    scope_text = _get_str(user, "scope") or ""
    scopes = [scope for scope in scope_text.split() if scope]
    docs_scope_detected = any(
        scope.startswith("docs:") or scope.startswith("docx:") for scope in scopes
    )
    drive_scope_detected = any(scope.startswith("drive:") for scope in scopes)
    return LarkCliUserStatus(
        available=bool(user.get("available")),
        verified=bool(user.get("verified")),
        status=_get_str(user, "status"),
        token_status=_get_str(user, "tokenStatus"),
        user_name=_get_str(user, "userName"),
        open_id_present=bool(_get_str(user, "openId")),
        scope_count=len(scopes),
        docs_scope_detected=docs_scope_detected,
        drive_scope_detected=drive_scope_detected,
        expires_at=_get_str(user, "expiresAt"),
        refresh_expires_at=_get_str(user, "refreshExpiresAt"),
    )


def _parse_json_object(text: str) -> dict[str, Any] | None:
    import json

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _get_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _display_executable(executable: str) -> str:
    name = os.path.basename(executable)
    return name or "lark-cli"


def _short_error(text: str, limit: int = 500) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


__all__ = [
    "LarkCliAuthStatus",
    "LarkCliUserStatus",
    "get_lark_cli_auth_status",
]
