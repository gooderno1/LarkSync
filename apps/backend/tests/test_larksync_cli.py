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


def test_do_bootstrap_cache_requires_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli,
        "do_check",
        lambda base_url: {
            "base_url": base_url,
            "health": {"ok": True, "status_code": 200, "data": {"status": "ok"}},
            "auth": {
                "ok": True,
                "status_code": 200,
                "data": {"connected": False, "drive_ok": None},
            },
            "config": {"ok": True, "status_code": 200, "data": {}},
            "tasks": {"ok": True, "status_code": 200, "count": 0, "data": []},
            "ready_for_sync": False,
        },
    )

    result = cli.do_bootstrap_cache(
        base_url="http://localhost:8000",
        name="Agent Cache",
        local_path=r"D:\Knowledge\FeishuMirror",
        cloud_folder_token="fld_test",
        sync_mode="download_only",
        download_value=1,
        download_unit="days",
        download_time="01:00",
        run_now=True,
    )

    assert result["action"] == "bootstrap-cache"
    assert result["phase"] == "needs_oauth"
    assert result["completed"] is False
    assert result["next_step"]["type"] == "complete_oauth"
    assert result["next_step"]["login_url"] == "http://localhost:8000/auth/login"


def test_do_bootstrap_cache_requires_drive_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "do_check",
        lambda base_url: {
            "base_url": base_url,
            "health": {"ok": True, "status_code": 200, "data": {"status": "ok"}},
            "auth": {
                "ok": True,
                "status_code": 200,
                "data": {"connected": True, "drive_ok": False, "account_name": "测试用户"},
            },
            "config": {"ok": True, "status_code": 200, "data": {}},
            "tasks": {"ok": True, "status_code": 200, "count": 0, "data": []},
            "ready_for_sync": True,
        },
    )

    result = cli.do_bootstrap_cache(
        base_url="http://localhost:8000",
        name="Agent Cache",
        local_path=r"D:\Knowledge\FeishuMirror",
        cloud_folder_token="fld_test",
        sync_mode="download_only",
        download_value=1,
        download_unit="days",
        download_time="01:00",
        run_now=False,
    )

    assert result["phase"] == "needs_drive_permission"
    assert result["completed"] is False
    assert result["next_step"]["type"] == "grant_drive_permission"


def test_do_bootstrap_cache_runs_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cli,
        "do_check",
        lambda base_url: {
            "base_url": base_url,
            "health": {"ok": True, "status_code": 200, "data": {"status": "ok"}},
            "auth": {
                "ok": True,
                "status_code": 200,
                "data": {"connected": True, "drive_ok": True, "account_name": "测试用户"},
            },
            "config": {"ok": True, "status_code": 200, "data": {}},
            "tasks": {"ok": True, "status_code": 200, "count": 0, "data": []},
            "ready_for_sync": True,
        },
    )

    def _fake_configure_download(*, base_url: str, value: float, unit: str, daily_time: str):
        calls.append("configure")
        return {"action": "config-set", "config": {"download_interval_unit": unit}}

    def _fake_create_task(**kwargs):
        calls.append("create")
        return {"action": "task-create", "created": True, "task": {"id": "task-1", **kwargs}}

    def _fake_run_task(base_url: str, task_id: str):
        calls.append("run")
        return {"action": "task-run", "task_id": task_id, "status": {"state": "queued"}}

    def _fake_task_status(base_url: str, task_id: str):
        calls.append("status")
        return {
            "action": "task-status",
            "task_id": task_id,
            "status": {"state": "running", "last_result": "ok"},
        }

    monkeypatch.setattr(cli, "do_configure_download", _fake_configure_download)
    monkeypatch.setattr(cli, "do_create_task", _fake_create_task)
    monkeypatch.setattr(cli, "do_run_task", _fake_run_task)
    monkeypatch.setattr(cli, "do_get_task_status", _fake_task_status)

    result = cli.do_bootstrap_cache(
        base_url="http://localhost:8000",
        name="Agent Cache",
        local_path=r"D:\Knowledge\FeishuMirror",
        cloud_folder_token="fld_test",
        sync_mode="download_only",
        download_value=1,
        download_unit="days",
        download_time="01:00",
        run_now=True,
    )

    assert result["phase"] == "configured"
    assert result["completed"] is True
    assert result["task"]["task"]["id"] == "task-1"
    assert result["run_now"]["task_id"] == "task-1"
    assert result["task_status"]["status"]["state"] == "running"
    assert calls == ["configure", "create", "run", "status"]


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


def test_main_supports_bootstrap_cache_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "do_bootstrap_cache",
        lambda **_: {
            "action": "bootstrap-cache",
            "phase": "configured",
            "completed": True,
        },
    )

    exit_code = cli.main(
        [
            "bootstrap-cache",
            "--local-path",
            r"D:\Knowledge\FeishuMirror",
            "--cloud-folder-token",
            "fld_test",
        ]
    )

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"action": "bootstrap-cache"' in payload
    assert '"completed": true' in payload.lower()


def test_do_list_workflow_templates() -> None:
    result = cli.do_list_workflow_templates()

    assert result["action"] == "workflow-template-list"
    assert result["total"] >= 3
    names = {item["name"] for item in result["items"]}
    assert {"daily-cache", "refresh-cache", "conflict-audit"} <= names


def test_do_get_workflow_template_daily_cache() -> None:
    result = cli.do_get_workflow_template("daily-cache")

    assert result["action"] == "workflow-template"
    assert result["template"] == "daily-cache"
    assert result["workflow"]["name"] == "daily-cache"
    step_commands = [step["command"] for step in result["workflow"]["steps"]]
    assert "bootstrap-cache" in step_commands
    assert any(branch["phase"] == "needs_oauth" for branch in result["workflow"]["branching"])


def test_do_get_workflow_template_invalid_name() -> None:
    with pytest.raises(ValueError, match="不支持"):
        cli.do_get_workflow_template("unknown-template")


def test_main_supports_workflow_template_list(
    capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(["workflow-template-list"])

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"action": "workflow-template-list"' in payload


def test_main_supports_workflow_template(
    capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(["workflow-template", "--template", "daily-cache"])

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"action": "workflow-template"' in payload
    assert '"template": "daily-cache"' in payload


def test_do_build_workflow_plan_daily_cache_helper() -> None:
    result = cli.do_build_workflow_plan(
        "daily-cache",
        entrypoint="helper",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
            "download_time": "02:30",
        },
    )

    assert result["action"] == "workflow-plan"
    assert result["template"] == "daily-cache"
    assert result["entrypoint"] == "helper"
    assert result["ready"] is True
    assert result["missing_inputs"] == []
    first_step = result["plan"]["steps"][0]
    assert first_step["ready"] is True
    assert "larksync_skill_helper.py bootstrap-cache" in first_step["command_line"]
    assert '--download-time "02:30"' in first_step["command_line"]
    second_step = result["plan"]["steps"][1]
    assert second_step["ready"] is False
    assert second_step["dynamic_inputs"][0]["from_step"] == "bootstrap"


def test_do_build_workflow_plan_reports_missing_inputs() -> None:
    result = cli.do_build_workflow_plan(
        "daily-cache",
        entrypoint="cli",
        values={"local_path": r"D:\Knowledge\FeishuMirror"},
    )

    assert result["ready"] is False
    assert "cloud_folder_token" in result["missing_inputs"]
    assert result["plan"]["steps"][0]["ready"] is False


def test_do_build_workflow_plan_invalid_entrypoint() -> None:
    with pytest.raises(ValueError, match="entrypoint"):
        cli.do_build_workflow_plan("daily-cache", entrypoint="invalid", values={})


def test_main_supports_workflow_plan(
    capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(
        [
            "workflow-plan",
            "--template",
            "daily-cache",
            "--entrypoint",
            "cli",
            "--set",
            r"local_path=D:\Knowledge\FeishuMirror",
            "--set",
            "cloud_folder_token=fld_test",
        ]
    )

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"action": "workflow-plan"' in payload
    assert '"template": "daily-cache"' in payload


def test_do_execute_workflow_resolves_dynamic_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_bootstrap_cache(**kwargs):
        calls.append(("bootstrap-cache", kwargs))
        return {
            "action": "bootstrap-cache",
            "task": {"task": {"id": "task-1"}},
            "phase": "configured",
        }

    def _fake_task_status(base_url: str, task_id: str):
        calls.append(("task-status", {"base_url": base_url, "task_id": task_id}))
        return {"action": "task-status", "task_id": task_id, "status": {"state": "running"}}

    monkeypatch.setattr(cli, "do_bootstrap_cache", _fake_bootstrap_cache)
    monkeypatch.setattr(cli, "do_get_task_status", _fake_task_status)

    result = cli.do_execute_workflow(
        template_name="daily-cache",
        entrypoint="cli",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
        },
        base_url="http://localhost:8000",
        dry_run=False,
    )

    assert result["action"] == "workflow-execute"
    assert result["completed"] is True
    assert result["executed_steps"] == 2
    assert result["results"]["bootstrap"]["task"]["task"]["id"] == "task-1"
    assert result["results"]["inspect-task"]["task_id"] == "task-1"
    assert calls == [
        (
            "bootstrap-cache",
            {
                "base_url": "http://localhost:8000",
                "name": "LarkSync Agent 本地缓存",
                "local_path": r"D:\Knowledge\FeishuMirror",
                "cloud_folder_token": "fld_test",
                "cloud_folder_name": None,
                "base_path": None,
                "sync_mode": "download_only",
                "update_mode": "auto",
                "md_sync_mode": None,
                "delete_policy": None,
                "delete_grace_minutes": None,
                "enabled": True,
                "is_test": False,
                "download_value": 1.0,
                "download_unit": "days",
                "download_time": "01:00",
                "run_now": True,
            },
        ),
        ("task-status", {"base_url": "http://localhost:8000", "task_id": "task-1"}),
    ]


def test_do_execute_workflow_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _fake_bootstrap_cache(**kwargs):
        called["value"] = True
        return kwargs

    monkeypatch.setattr(cli, "do_bootstrap_cache", _fake_bootstrap_cache)

    result = cli.do_execute_workflow(
        template_name="daily-cache",
        entrypoint="helper",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
        },
        base_url="http://localhost:8000",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["executed_steps"] == 0
    assert result["completed"] is False
    assert called["value"] is False
    assert result["plan"]["steps"][0]["ready"] is True


def test_main_supports_workflow_execute(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "do_execute_workflow",
        lambda **_: {
            "action": "workflow-execute",
            "template": "daily-cache",
            "completed": True,
            "executed_steps": 1,
        },
    )

    exit_code = cli.main(
        [
            "workflow-execute",
            "--template",
            "daily-cache",
            "--set",
            r"local_path=D:\Knowledge\FeishuMirror",
            "--set",
            "cloud_folder_token=fld_test",
        ]
    )

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"action": "workflow-execute"' in payload


def test_do_execute_workflow_respects_step_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cli,
        "do_get_task_status",
        lambda base_url, task_id: calls.append("task-status") or {"task_id": task_id},
    )
    monkeypatch.setattr(
        cli,
        "do_read_sync_logs",
        lambda base_url, **kwargs: calls.append("logs-sync") or {"items": [], **kwargs},
    )

    result = cli.do_execute_workflow(
        template_name="refresh-cache",
        entrypoint="cli",
        values={"task_id": "task-1", "log_limit": 10},
        base_url="http://localhost:8000",
        from_step="task-status",
        to_step="sync-logs",
    )

    assert result["completed"] is True
    assert result["executed_steps"] == 2
    assert list(result["results"]) == ["task-status", "sync-logs"]
    assert calls == ["task-status", "logs-sync"]


def test_do_execute_workflow_continue_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fail_run_task(base_url: str, task_id: str):
        calls.append("run-task")
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "do_run_task", _fail_run_task)
    monkeypatch.setattr(
        cli,
        "do_get_task_status",
        lambda base_url, task_id: calls.append("task-status") or {"task_id": task_id},
    )
    monkeypatch.setattr(
        cli,
        "do_read_sync_logs",
        lambda base_url, **kwargs: calls.append("logs-sync") or {"items": [], **kwargs},
    )

    result = cli.do_execute_workflow(
        template_name="refresh-cache",
        entrypoint="cli",
        values={"task_id": "task-1", "log_limit": 10},
        base_url="http://localhost:8000",
        continue_on_error=True,
    )

    assert result["completed"] is False
    assert result["failed_steps"] == 1
    assert result["errors"][0]["step_id"] == "run-task"
    assert list(result["results"]) == ["task-status", "sync-logs"]
    assert calls == ["run-task", "task-status", "logs-sync"]


def test_do_execute_workflow_writes_output_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "workflow.json"

    result = cli.do_execute_workflow(
        template_name="daily-cache",
        entrypoint="cli",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
        },
        base_url="http://localhost:8000",
        dry_run=True,
        output_json_file=output_path,
    )

    assert result["dry_run"] is True
    assert output_path.is_file()
    payload = output_path.read_text(encoding="utf-8")
    assert '"action": "workflow-execute"' in payload


def test_main_supports_workflow_execute_controls(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    captured: list[dict[str, object]] = []

    def _fake_execute(**kwargs):
        captured.append(kwargs)
        return {"action": "workflow-execute", "completed": False, "executed_steps": 0}

    monkeypatch.setattr(cli, "do_execute_workflow", _fake_execute)
    output_path = tmp_path / "workflow.json"

    exit_code = cli.main(
        [
            "workflow-execute",
            "--template",
            "daily-cache",
            "--from-step",
            "bootstrap",
            "--to-step",
            "inspect-task",
            "--continue-on-error",
            "--output-json-file",
            str(output_path),
            "--set",
            r"local_path=D:\Knowledge\FeishuMirror",
            "--set",
            "cloud_folder_token=fld_test",
        ]
    )

    assert exit_code == 0
    assert captured == [
        {
            "template_name": "daily-cache",
            "entrypoint": "cli",
            "values": {
                "local_path": r"D:\Knowledge\FeishuMirror",
                "cloud_folder_token": "fld_test",
            },
            "base_url": "http://localhost:8000",
            "dry_run": False,
            "from_step": "bootstrap",
            "to_step": "inspect-task",
            "continue_on_error": True,
            "output_json_file": output_path,
            "run_id": None,
            "resume_from_file": None,
            "skip_completed": False,
        }
    ]
    payload = capsys.readouterr().out
    assert '"action": "workflow-execute"' in payload


def test_do_execute_workflow_persists_and_resumes_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def _fake_bootstrap_cache(**kwargs):
        calls.append("bootstrap-cache")
        return {
            "action": "bootstrap-cache",
            "task": {"task": {"id": "task-1"}},
            "phase": "configured",
        }

    def _fake_task_status(base_url: str, task_id: str):
        calls.append("task-status")
        return {"action": "task-status", "task_id": task_id, "status": {"state": "running"}}

    monkeypatch.setattr(cli, "do_bootstrap_cache", _fake_bootstrap_cache)
    monkeypatch.setattr(cli, "do_get_task_status", _fake_task_status)

    output_path = tmp_path / "resume.json"
    first = cli.do_execute_workflow(
        template_name="daily-cache",
        entrypoint="cli",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
        },
        base_url="http://localhost:8000",
        dry_run=False,
        output_json_file=output_path,
    )

    calls.clear()

    second = cli.do_execute_workflow(
        template_name="daily-cache",
        entrypoint="cli",
        values={
            "local_path": r"D:\Knowledge\FeishuMirror",
            "cloud_folder_token": "fld_test",
        },
        base_url="http://localhost:8000",
        dry_run=False,
        run_id=str(first["run_id"]),
        output_json_file=output_path,
        resume_from_file=output_path,
        skip_completed=True,
    )

    assert first["completed"] is True
    assert second["completed"] is True
    assert second["run_id"] == first["run_id"]
    assert second["resumed"] is True
    assert second["executed_steps"] == 0
    assert second["skipped_steps"] == 2
    assert calls == []


def test_do_execute_workflow_skip_completed_without_resume_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cli,
        "do_get_task_status",
        lambda base_url, task_id: calls.append("task-status") or {"task_id": task_id},
    )
    monkeypatch.setattr(
        cli,
        "do_read_sync_logs",
        lambda base_url, **kwargs: calls.append("logs-sync") or {"items": [], **kwargs},
    )

    result = cli.do_execute_workflow(
        template_name="refresh-cache",
        entrypoint="cli",
        values={"task_id": "task-1"},
        base_url="http://localhost:8000",
        from_step="task-status",
        skip_completed=True,
    )

    assert result["completed"] is True
    assert result["executed_steps"] == 2
    assert result["skipped_steps"] == 0
    assert calls == ["task-status", "logs-sync"]


def test_main_supports_workflow_execute_resume_options(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    captured: list[dict[str, object]] = []

    def _fake_execute(**kwargs):
        captured.append(kwargs)
        return {
            "action": "workflow-execute",
            "completed": True,
            "executed_steps": 0,
            "skipped_steps": 2,
            "run_id": "run-1",
        }

    monkeypatch.setattr(cli, "do_execute_workflow", _fake_execute)
    output_path = tmp_path / "workflow.json"

    exit_code = cli.main(
        [
            "workflow-execute",
            "--template",
            "daily-cache",
            "--run-id",
            "run-1",
            "--resume-from-file",
            str(output_path),
            "--skip-completed",
            "--set",
            r"local_path=D:\Knowledge\FeishuMirror",
            "--set",
            "cloud_folder_token=fld_test",
        ]
    )

    assert exit_code == 0
    assert captured == [
        {
            "template_name": "daily-cache",
            "entrypoint": "cli",
            "values": {
                "local_path": r"D:\Knowledge\FeishuMirror",
                "cloud_folder_token": "fld_test",
            },
            "base_url": "http://localhost:8000",
            "dry_run": False,
            "from_step": None,
            "to_step": None,
            "continue_on_error": False,
            "output_json_file": None,
            "run_id": "run-1",
            "resume_from_file": output_path,
            "skip_completed": True,
        }
    ]
    payload = capsys.readouterr().out
    assert '"run_id": "run-1"' in payload
