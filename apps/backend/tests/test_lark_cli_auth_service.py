from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from src.services.lark_cli_auth_service import get_lark_cli_auth_status


@dataclass
class _Completed:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def test_lark_cli_status_reports_missing_cli() -> None:
    status = get_lark_cli_auth_status(which=lambda _name: None)

    assert status.installed is False
    assert status.can_assist_oauth is False
    assert status.user is None
    assert "未检测到" in status.message


def test_lark_cli_status_parses_user_status_without_exposing_open_id() -> None:
    payload = {
        "brand": "feishu",
        "identity": "user",
        "verified": True,
        "identities": {
            "user": {
                "available": True,
                "verified": True,
                "status": "ready",
                "tokenStatus": "valid",
                "userName": "测试用户",
                "openId": "ou_secret",
                "scope": "drive:file:download drive:file:upload docx:document:readonly",
                "expiresAt": "2026-07-07T10:00:00+08:00",
                "refreshExpiresAt": "2026-07-14T10:00:00+08:00",
            }
        },
    }

    def fake_run(command, **_kwargs):
        assert command == [
            "C:/tools/lark-cli.cmd",
            "auth",
            "status",
            "--json",
            "--verify",
        ]
        return _Completed(returncode=0, stdout=json.dumps(payload))

    status = get_lark_cli_auth_status(
        which=lambda _name: "C:/tools/lark-cli.cmd",
        run=fake_run,
    )

    assert status.installed is True
    assert status.executable == "lark-cli.cmd"
    assert status.identity == "user"
    assert status.can_assist_oauth is True
    assert status.user is not None
    assert status.user.user_name == "测试用户"
    assert status.user.open_id_present is True
    assert status.user.scope_count == 3
    assert status.user.docs_scope_detected is True
    assert status.user.drive_scope_detected is True
    assert "ou_secret" not in status.model_dump_json()


def test_lark_cli_status_handles_command_failure() -> None:
    def fake_run(_command, **_kwargs):
        return _Completed(returncode=1, stderr="not logged in")

    status = get_lark_cli_auth_status(
        which=lambda _name: "lark-cli",
        run=fake_run,
    )

    assert status.installed is True
    assert status.can_assist_oauth is False
    assert status.last_error == "not logged in"


def test_lark_cli_status_handles_timeout() -> None:
    def fake_run(_command, **_kwargs):
        raise subprocess.TimeoutExpired(["lark-cli"], timeout=6)

    status = get_lark_cli_auth_status(
        which=lambda _name: "lark-cli",
        run=fake_run,
    )

    assert status.installed is True
    assert status.last_error == "timeout"
