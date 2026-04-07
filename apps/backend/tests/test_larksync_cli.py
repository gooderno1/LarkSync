from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = ROOT / "scripts" / "larksync_cli.py"

spec = importlib.util.spec_from_file_location("larksync_cli", CLI_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"无法加载脚本模块: {CLI_PATH}")
cli = importlib.util.module_from_spec(spec)
sys.modules["larksync_cli"] = cli
spec.loader.exec_module(cli)


def test_validate_base_url_localhost_default() -> None:
    assert cli.validate_base_url("http://localhost:8000") == "http://localhost:8000"
    assert cli.validate_base_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert cli.validate_base_url("http://[::1]:8000/") == "http://[::1]:8000"


def test_validate_base_url_reject_remote_by_default() -> None:
    with pytest.raises(ValueError, match="localhost"):
        cli.validate_base_url("https://example.com")


def test_validate_base_url_allow_remote_with_opt_in() -> None:
    assert (
        cli.validate_base_url("https://example.com", allow_remote=True)
        == "https://example.com"
    )


def test_build_download_config_payload_days() -> None:
    payload = cli.build_download_config_payload(1, "days", "02:30")
    assert payload == {
        "download_interval_value": 1.0,
        "download_interval_unit": "days",
        "download_daily_time": "02:30",
    }


def test_build_download_config_payload_invalid_daily_time() -> None:
    with pytest.raises(ValueError):
        cli.build_download_config_payload(1, "days", "2:70")


def test_build_task_payload_download_only() -> None:
    payload = cli.build_task_payload(
        name="Demo",
        local_path=r"C:\data\docs",
        cloud_folder_token="fld_xxx",
        sync_mode="download_only",
    )
    assert payload["name"] == "Demo"
    assert payload["local_path"].lower().endswith(r"c:\data\docs".lower())
    assert payload["cloud_folder_token"] == "fld_xxx"
    assert payload["sync_mode"] == "download_only"
    assert payload["md_sync_mode"] == "download_only"


def test_build_task_payload_invalid_mode() -> None:
    with pytest.raises(ValueError):
        cli.build_task_payload(
            name="Demo",
            local_path=r"C:\data\docs",
            cloud_folder_token="fld_xxx",
            sync_mode="invalid",
        )


def test_do_update_install_prefers_explicit_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, dict[str, object] | None]] = []

    def _fake_request_json(
        *,
        base_url: str,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        timeout: float = 15.0,
    ):
        calls.append((base_url, method, path, payload))
        return cli.ApiResult(
            ok=True,
            status_code=200,
            data={"queued": True, "installer_path": r"D:\pkg.exe"},
        )

    monkeypatch.setattr(cli, "_request_json", _fake_request_json)

    result = cli.do_update_install("http://localhost:8000", r"D:\pkg.exe")

    assert result["action"] == "update-install"
    assert calls == [
        (
            "http://localhost:8000",
            "POST",
            "/system/update/install",
            {"download_path": r"D:\pkg.exe"},
        )
    ]


def test_do_task_update_builds_patch_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, dict[str, object] | None]] = []

    def _fake_request_json(
        *,
        base_url: str,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        timeout: float = 15.0,
    ):
        calls.append((base_url, method, path, payload))
        return cli.ApiResult(ok=True, status_code=200, data={"id": "task-1", **(payload or {})})

    monkeypatch.setattr(cli, "_request_json", _fake_request_json)

    result = cli.do_update_task(
        base_url="http://localhost:8000",
        task_id="task-1",
        name="新任务名",
        sync_mode="download_only",
        enabled=False,
    )

    assert result["action"] == "task-update"
    assert calls == [
        (
            "http://localhost:8000",
            "PATCH",
            "/sync/tasks/task-1",
            {
                "name": "新任务名",
                "sync_mode": "download_only",
                "enabled": False,
            },
        )
    ]


def test_main_supports_task_list_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "do_list_tasks",
        lambda base_url: {
            "action": "task-list",
            "items": [{"id": "task-1"}],
            "total": 1,
        },
    )

    exit_code = cli.main(["task-list"])

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"ok": true' in payload.lower()
    assert '"action": "task-list"' in payload

