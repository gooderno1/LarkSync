"""Agent contracts: no credentials, preview without I/O, portable distribution."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = ROOT / "integrations/skills/larksync/scripts/larksync_cli.py"
spec = importlib.util.spec_from_file_location("ai_cli_under_test", CLI_PATH)
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cli
spec.loader.exec_module(cli)


def invoke(capsys, *args):
    code = cli.main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_argument_errors_are_json(capsys):
    code, output = invoke(capsys, "task-status")
    assert code == 2
    assert output["ok"] is False
    assert output["error_code"] == "INVALID_ARGUMENT"


def test_capabilities_offline_explains_global_schedule(monkeypatch, capsys):
    monkeypatch.setattr(cli.request, "urlopen", lambda *a, **k: pytest.fail("network"))
    code, output = invoke(capsys, "capabilities")
    assert code == 0
    assert output["result"]["schedule_scope"] == "global"
    assert "task-plan" in output["result"]["commands"]


def test_old_backend_html_fallback_reports_incompatible_response(monkeypatch, capsys):
    response = Response({})
    response.read = lambda: b"<!doctype html><html>old app</html>"
    monkeypatch.setattr(cli.request, "urlopen", lambda *a, **kw: response)
    code, output = invoke(capsys, "schema")
    assert code == 1
    assert output["error_code"] == "INVALID_RESPONSE"
    assert "1.0.0" in output["next_step"]


def test_plan_normalizes_url_and_preserves_rules_without_io(tmp_path, monkeypatch, capsys):
    spec_file = tmp_path / "task.json"
    spec_file.write_text(json.dumps({
        "local_path": str(tmp_path / "cache"),
        "cloud_folder_token": "https://example.feishu.cn/drive/folder/fld123?x=1",
        "ignored_subpaths": ["private"],
        "path_sync_rules": [{"path": "docs", "kind": "folder", "sync_mode": "download_only"}],
    }), encoding="utf-8")
    monkeypatch.setattr(cli.request, "urlopen", lambda *a, **k: pytest.fail("preview network"))
    code, output = invoke(capsys, "task-plan", "--spec-file", str(spec_file))
    assert code == 0
    result = output["result"]
    assert result["dry_run"] and result["ready"]
    assert result["payload"]["cloud_folder_token"] == "fld123"
    assert result["payload"]["sync_mode"] == "download_only"
    assert result["payload"]["delete_policy"] == "off"
    assert result["payload"]["path_sync_rules"][0]["path"] == "docs"
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("patch", [
    {"unknown": True}, {"enabled": "false"}, {"ignored_subpaths": ["../secret"]},
    {"path_sync_rules": [{"path": "x", "kind": "folder", "sync_mode": "invalid"}]},
    {"cloud_folder_token": "https://example.feishu.cn/docx/abc"},
    {"local_path": "relative/cache"},
])
def test_invalid_spec_cannot_write(patch, tmp_path, monkeypatch, capsys):
    value = {"local_path": str(tmp_path / "cache"), "cloud_folder_token": "fld1", **patch}
    spec_file = tmp_path / "task.json"
    spec_file.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(cli.request, "urlopen", lambda *a, **k: pytest.fail("invalid spec network"))
    code, output = invoke(capsys, "task-create", "--spec-file", str(spec_file))
    assert code == 2
    assert not output["ok"]


def test_plan_returns_missing_inputs(capsys):
    code, output = invoke(capsys, "task-plan")
    assert code == 0
    assert set(output["result"]["missing_inputs"]) == {"local_path", "cloud_folder_token"}
    assert not output["result"]["ready"]


def test_update_preview_does_not_assume_existing_direction(capsys):
    code, output = invoke(capsys, "task-update", "--task-id", "t1", "--name", "renamed", "--dry-run")
    assert code == 0
    assert output["result"]["effects"]["may_write_cloud"] == "depends_on_existing_task"


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self.data).encode()

    def getcode(self):
        return 200


def test_multia_account_requires_choice_before_write(monkeypatch, capsys):
    calls = []

    def send(req, **kwargs):
        calls.append(req)
        assert req.full_url.endswith("/accounts")
        return Response([{"id": "a"}, {"id": "b"}])

    monkeypatch.setattr(cli.request, "urlopen", send)
    code, output = invoke(capsys, "task-pause", "--task-id", "t1")
    assert code == 1
    assert output["error_code"] == "ACCOUNT_REQUIRED"
    assert len(calls) == 1


def test_account_header_stays_pinned_through_wait(monkeypatch, capsys):
    calls = []
    statuses = iter([
        {"state": "running", "current_run_id": "r1"},
        {"state": "success", "current_run_id": "r1", "finished_at": 100},
    ])

    def send(req, **kwargs):
        calls.append(req)
        if req.full_url.endswith("/accounts"):
            return Response([{"id": "a"}, {"id": "b"}])
        assert req.get_header("X-larksync-account-id") == "b"
        return Response(next(statuses))

    monkeypatch.setattr(cli.request, "urlopen", send)
    code, output = invoke(capsys, "--account-id", "b", "task-run", "--task-id", "t1",
                          "--wait", "--poll-interval", "0.01", "--timeout", "1")
    assert code == 0
    assert output["result"]["sync_complete"] is True
    assert output["account_id"] == "b"
    assert sum(r.full_url.endswith("/accounts") for r in calls) == 1


def test_wait_timeout_does_not_claim_completion(monkeypatch, capsys):
    def send(req, **kwargs):
        if req.full_url.endswith("/accounts"):
            return Response([{"id": "a"}])
        return Response({"state": "idle", "finished_at": None})

    monkeypatch.setattr(cli.request, "urlopen", send)
    code, output = invoke(capsys, "task-wait", "--task-id", "t1", "--timeout", "0")
    assert code == 0
    assert output["result"]["timed_out"]
    assert output["result"]["sync_complete"] is False


def test_wait_detects_replaced_run(monkeypatch, capsys):
    monkeypatch.setattr(cli.request, "urlopen", lambda req, **kw: Response(
        [{"id": "a"}] if req.full_url.endswith("/accounts") else
        {"state": "success", "current_run_id": "new-run", "finished_at": 123}
    ))
    code, output = invoke(capsys, "task-wait", "--task-id", "t1", "--run-id", "old-run")
    assert code == 1
    assert output["error_code"] == "RUN_REPLACED"


def test_device_auth_and_registration_do_not_need_existing_account(monkeypatch, capsys):
    calls = []
    def send(req, **kwargs):
        calls.append(req)
        return Response({"session_id": "s1", "status": "pending", "interval": 5})
    monkeypatch.setattr(cli.request, "urlopen", send)
    assert invoke(capsys, "auth-start", "--app-profile-id", "app1")[0] == 0
    assert calls[-1].full_url.endswith("/auth/device-sessions")
    assert json.loads(calls[-1].data) == {"app_profile_id": "app1"}
    assert invoke(capsys, "auth-start", "--register", "--brand", "lark")[0] == 0
    assert calls[-1].full_url.endswith("/app-profiles/registration-sessions")


def test_spec_update_can_clear_rules_without_default_changes(tmp_path, monkeypatch, capsys):
    spec_file = tmp_path / "patch.json"
    spec_file.write_text('{"ignored_subpaths": [], "path_sync_rules": []}', encoding="utf-8")
    calls = []
    def send(req, **kwargs):
        if req.full_url.endswith("/accounts"):
            return Response([{"id": "a"}])
        calls.append(req)
        return Response({"id": "t1", **json.loads(req.data)})
    monkeypatch.setattr(cli.request, "urlopen", send)
    assert invoke(capsys, "task-update", "--task-id", "t1", "--spec-file", str(spec_file))[0] == 0
    assert json.loads(calls[0].data) == {"ignored_subpaths": [], "path_sync_rules": []}


def test_skill_survives_copy_without_repository(tmp_path):
    source = ROOT / "integrations/skills/larksync"
    target = tmp_path / "user/skills/larksync"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    result = subprocess.run(
        [sys.executable, str(target / "scripts/larksync_cli.py"), "capabilities"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"]
