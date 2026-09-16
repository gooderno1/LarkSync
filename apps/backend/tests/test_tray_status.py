import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Generator
from unittest.mock import AsyncMock

# 确保从任意工作目录运行 pytest 时都能找到 src 包
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from fastapi.testclient import TestClient

from src.core.config import ConfigManager
from src.db.session import get_session_maker
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_run_service import SyncRunService
from src.services.sync_runner import SyncFileEvent, SyncTaskStatus


@pytest.fixture
def tray_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    """
    独立构建一份使用临时 SQLite 的 app，以免写入真实数据目录。
    """
    monkeypatch.setenv("LARKSYNC_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LARKSYNC_UPDATE_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("LARKSYNC_TOKEN_STORE", "file")

    # 确保配置单例与 API 模块按新的环境重载，避免复用旧 service/runner 实例。
    ConfigManager.reset()
    stale_modules = [
        name
        for name in list(sys.modules)
        if name == "src.main" or name == "src.api" or name.startswith("src.api.")
    ]
    for name in stale_modules:
        sys.modules.pop(name, None)
    main = importlib.import_module("src.main")

    with TestClient(main.app) as client:
        yield client

    # 恢复默认配置单例并重载 main，避免影响其他用例。
    ConfigManager.reset()
    for name in [
        n
        for n in list(sys.modules)
        if n == "src.main" or n == "src.api" or n.startswith("src.api.")
    ]:
        sys.modules.pop(name, None)
    importlib.import_module("src.main")


def test_tray_status_conflict_count(
    tray_client: TestClient, monkeypatch
) -> None:
    import src.api.conflicts as conflicts_api

    async def fake_resolve_conflict(conflict_id: str, action: str, *, runner):
        return await conflicts_api.service.resolve(conflict_id, action)

    monkeypatch.setattr(
        conflicts_api.resolution_service,
        "resolve_conflict",
        fake_resolve_conflict,
    )

    # 创建一条冲突记录
    payload = {
        "local_path": "/tmp/demo.md",
        "cloud_token": "doccnTestToken",
        "local_hash": "localhash",
        "db_hash": "dbhash",
        "cloud_version": 2,
        "db_version": 1,
        "local_preview": "local preview",
        "cloud_preview": "cloud preview",
    }
    resp = tray_client.post("/conflicts", json=payload)
    assert resp.status_code == 200
    conflict_id = resp.json()["id"]

    # 冲突先由统一问题服务归档，再由所有展示入口读取同一摘要。
    tray_client.get("/problems/summary?refresh=true")

    # /tray/status 应返回未解决冲突数量
    status = tray_client.get("/tray/status").json()
    assert status["unresolved_conflicts"] == 1

    # 解决冲突后，数量应变为 0
    resolve = tray_client.post(f"/conflicts/{conflict_id}/resolve", json={"action": "use_cloud"})
    assert resolve.status_code == 200
    tray_client.get("/problems/summary?refresh=true")

    status_after = tray_client.get("/tray/status").json()
    assert status_after["unresolved_conflicts"] == 0


def test_desktop_and_tray_counts_share_problem_lifecycle_and_account_scope(
    tray_client: TestClient, monkeypatch
) -> None:
    import src.main as main
    from src.db.models import ConflictRecord, ProblemRecord

    async def seed() -> None:
        async with get_session_maker()() as session:
            for index, (account, state, category) in enumerate([
                ("account-a", "resolved", "conflict"),
                ("account-a", "resolved", "conflict"),
                ("account-a", "ignored", "conflict"),
                ("account-b", "open", "conflict"),
                ("account-b", "in_progress", "upload"),
                ("account-b", "waiting", "local_io"),
            ]):
                session.add(ProblemRecord(
                    id=f"problem-{index}", account_id=account,
                    fingerprint=f"fingerprint-{index}", category=category,
                    severity="high", state=state, title="测试问题", summary="测试",
                    object_kind="conflict" if category == "conflict" else "sync_object",
                    object_key=f"file-{index}.md", first_seen_at=1.0,
                    last_seen_at=1.0, classifier_version="test",
                    resolution_verification="path_excluded" if state == "resolved" else None,
                ))
            for index in range(3):
                session.add(ConflictRecord(
                    id=f"conflict-{index}", account_id="account-a",
                    local_path=f"node_modules/file-{index}.md", cloud_token=f"token-{index}",
                    local_hash="local", db_hash="baseline", cloud_version=2, db_version=1,
                    local_preview="保留本地证据", cloud_preview="保留云端证据",
                    created_at=1.0, resolved=False,
                ))
            await session.commit()

    asyncio.run(seed())
    monkeypatch.setattr(main.sync_runner, "list_statuses", lambda: {
        "old-task": SyncTaskStatus(task_id="old-task", state="failed", last_error="历史失败")
    })
    # 统计接口必须只读摘要，不扫描旧冲突，也不触发历史回填。
    monkeypatch.setattr(main.conflict_service, "list_conflicts", AsyncMock(
        side_effect=AssertionError("统计不应读取旧冲突队列")
    ))
    monkeypatch.setattr(main.problem_service, "refresh_sources", AsyncMock(
        side_effect=AssertionError("状态查询不应回填历史")
    ))
    for account, count, conflicts in [("account-a", 0, 0), ("account-b", 3, 1)]:
        headers = {"X-LarkSync-Account-ID": account}
        summary = tray_client.get("/problems/summary", headers=headers).json()
        desktop = tray_client.get("/system/desktop/status", headers=headers).json()
        tray = tray_client.get("/tray/status", headers=headers).json()
        assert summary["unresolved"] == desktop["problems"]["unresolved"] == tray["unresolved_problems"] == count
        assert desktop["conflicts"]["unresolved"] == tray["unresolved_conflicts"] == conflicts
        assert tray["last_error"] == "历史失败"  # 诊断信息保留，但不构成待处理计数。

    async def check_original_conflicts() -> None:
        async with get_session_maker()() as session:
            for index in range(3):
                conflict = await session.get(ConflictRecord, f"conflict-{index}")
                assert conflict and not conflict.resolved
                assert conflict.local_preview == "保留本地证据"
                assert conflict.cloud_preview == "保留云端证据"
    asyncio.run(check_original_conflicts())


def test_tray_status_does_not_report_zero_when_problem_summary_fails(
    tray_client: TestClient, monkeypatch
) -> None:
    import src.main as main

    monkeypatch.setattr(main.problem_service, "get_summary", AsyncMock(
        side_effect=RuntimeError("summary unavailable")
    ))
    response = tray_client.get("/tray/status")
    assert response.status_code == 503
    assert "unresolved_problems" not in response.json()


@pytest.mark.parametrize(("payload", "expected"), [
    ({"unresolved_problems": 0, "last_error": "历史错误"}, "idle"),
    ({"unresolved_problems": 0, "tasks_running": 1}, "syncing"),
    ({"unresolved_problems": 1, "unresolved_conflicts": 0}, "error"),
    ({"unresolved_problems": 1, "tasks_running": 1}, "error"),
    ({"unresolved_problems": 1, "unresolved_conflicts": 1}, "error"),
    ({"last_error": None}, "error"),
    ({"unresolved_problems": None}, "error"),
    ({"unresolved_problems": 0, "backend_running": False}, "error"),
    (None, "error"),
])
def test_tray_poll_uses_current_problems_instead_of_historical_errors(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, object] | None, expected: str
) -> None:
    from apps.tray import tray_app

    tray = object.__new__(tray_app.LarkSyncTray)
    tray._running = True
    tray._last_conflict_count = 0
    tray._backend = SimpleNamespace(maybe_auto_restart=lambda: False)
    states = []
    notifications = []
    status = None if payload is None else {"backend_running": True, **payload}
    monkeypatch.setattr(tray, "_handle_pending_install_request", lambda: False)
    monkeypatch.setattr(tray, "_fetch_tray_status", lambda: status)
    monkeypatch.setattr(tray, "_set_state", states.append)
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: notifications.append(args))
    monkeypatch.setattr(tray_app.time, "sleep", lambda _: setattr(tray, "_running", False))
    tray._poll_status_loop()
    assert states == [expected]
    assert len(notifications) == int(bool(payload and payload.get("unresolved_conflicts")))


def test_tray_clears_problem_state_and_does_not_repeat_conflict_notifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.tray import tray_app

    tray = object.__new__(tray_app.LarkSyncTray)
    tray._running = True
    tray._last_conflict_count = 0
    tray._backend = SimpleNamespace(maybe_auto_restart=lambda: False)
    samples = iter([
        {"backend_running": True, "unresolved_problems": 1, "unresolved_conflicts": 1},
        {"backend_running": True, "unresolved_problems": 1, "unresolved_conflicts": 1},
        {"backend_running": True, "unresolved_problems": 0, "unresolved_conflicts": 0,
         "last_error": "上次运行的历史错误"},
    ])
    states: list[str] = []
    notices: list[tuple] = []
    monkeypatch.setattr(tray, "_handle_pending_install_request", lambda: False)
    monkeypatch.setattr(tray, "_fetch_tray_status", lambda: next(samples))
    monkeypatch.setattr(tray, "_set_state", states.append)
    monkeypatch.setattr(tray, "_notify", lambda *args, **kwargs: notices.append(args))
    monkeypatch.setattr(tray_app.time, "sleep", lambda _: setattr(tray, "_running", len(states) < 3))
    tray._poll_status_loop()
    assert states == ["error", "error", "idle"]
    assert len(notices) == 1
    assert tray._last_conflict_count == 0


def test_tray_status_ignores_stale_running_state_for_disabled_tasks(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.main as main

    local_dir = tmp_path / "local"
    local_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "name": "任务A",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-a",
        "cloud_folder_name": "云端A",
        "base_path": None,
        "sync_mode": "download_only",
        "update_mode": "auto",
        "enabled": False,
    }
    payload_b = dict(payload)
    payload_b["name"] = "任务B"
    payload_b["local_path"] = str(tmp_path / "local-b")
    payload_b["cloud_folder_token"] = "token-b"

    resp_a = tray_client.post("/sync/tasks", json=payload)
    resp_b = tray_client.post("/sync/tasks", json=payload_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    task_a = resp_a.json()["id"]
    task_b = resp_b.json()["id"]

    statuses = {
        task_a: SyncTaskStatus(task_id=task_a, state="failed", last_error="boom"),
        task_b: SyncTaskStatus(task_id=task_b, state="running"),
    }
    monkeypatch.setattr(main.sync_runner, "list_statuses", lambda: statuses)

    status = tray_client.get("/tray/status").json()
    assert status["tasks_total"] == 2
    assert status["tasks_paused"] == 2
    assert status["tasks_running"] == 0
    assert status["last_error"] == "boom"


def test_desktop_status_aggregates_shell_state(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.main as main

    local_dir = tmp_path / "desktop-status-local"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "桌面状态任务",
        "local_path": str(local_dir),
        "cloud_folder_token": "desktop-token",
        "cloud_folder_name": "桌面状态云端",
        "base_path": None,
        "sync_mode": "download_only",
        "update_mode": "auto",
        "enabled": True,
    }
    created = tray_client.post("/sync/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]
    monkeypatch.setattr(
        main.sync_runner,
        "list_statuses",
        lambda: {
            task_id: SyncTaskStatus(
                task_id=task_id,
                state="running",
                finished_at=123.0,
            )
        },
    )

    response = tray_client.get("/system/desktop/status")
    assert response.status_code == 200
    body = response.json()
    assert body["runtime"]["backend_running"] is True
    assert body["runtime"]["data_dir"].endswith("data")
    assert body["runtime"]["profile"] == "production"
    assert body["runtime"]["cloud_write_policy"] == "normal"
    assert body["auth"]["connected"] is False
    assert body["auth"]["device_id"]
    assert body["tasks"]["total"] == 1
    assert body["tasks"]["enabled"] == 1
    assert body["tasks"]["running"] == 1
    assert body["tasks"]["last_sync_time"] == 123.0
    assert body["conflicts"]["unresolved"] == 0
    assert body["update"]["current_version"]

    tray_response = tray_client.get("/tray/status")
    assert tray_response.status_code == 200
    tray_body = tray_response.json()
    assert tray_body["tasks_total"] == body["tasks"]["total"]
    assert tray_body["tasks_running"] == body["tasks"]["running"]


def test_sync_task_status_includes_delete_counters(
    tray_client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    import src.api.sync_tasks as sync_tasks

    local_dir = tmp_path / "delete-status"
    local_dir.mkdir()
    created = tray_client.post(
        "/sync/tasks",
        json={
            "name": "删除状态测试",
            "local_path": str(local_dir),
            "cloud_folder_token": "delete-status-token",
            "sync_mode": "download_only",
            "update_mode": "auto",
            "enabled": False,
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]
    status = SyncTaskStatus(
        task_id=task_id,
        state="running",
        started_at=10.0,
        total_files=6,
        completed_files=2,
        failed_files=1,
        skipped_files=0,
        uploaded_files=1,
        downloaded_files=1,
        deleted_files=2,
        conflict_files=1,
        delete_pending_files=1,
        delete_failed_files=1,
        current_run_id="run-delete",
        last_files=[
            SyncFileEvent(path="D:/docs/removed.md", status="deleted", timestamp=11.0),
        ],
    )
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: status})

    response = tray_client.get("/sync/tasks/status")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["task_id"] == task_id
    assert body[0]["uploaded_files"] == 1
    assert body[0]["downloaded_files"] == 1
    assert body[0]["deleted_files"] == 2
    assert body[0]["conflict_files"] == 1
    assert body[0]["delete_pending_files"] == 1
    assert body[0]["delete_failed_files"] == 1


def test_create_task_rejects_duplicate_mapping(tray_client: TestClient, tmp_path: Path) -> None:
    local_dir = tmp_path / "duplicate-local"
    local_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "name": "任务A",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-a",
        "cloud_folder_name": "我的空间/A",
        "base_path": None,
        "sync_mode": "download_only",
        "update_mode": "auto",
        "enabled": False,
    }
    first = tray_client.post("/sync/tasks", json=payload)
    assert first.status_code == 200

    duplicate = dict(payload)
    duplicate["name"] = "任务B"
    duplicate["cloud_folder_token"] = "token-b"
    resp = tray_client.post("/sync/tasks", json=duplicate)
    assert resp.status_code == 409


def test_sync_task_overview_and_diagnostics(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.api.sync_tasks as sync_tasks

    local_dir = tmp_path / "diagnostics-local"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "诊断任务",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-diagnostics",
        "cloud_folder_name": "云端诊断",
        "base_path": None,
        "sync_mode": "bidirectional",
        "update_mode": "auto",
        "enabled": False,
    }
    created = tray_client.post("/sync/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]

    store = SyncEventStore(tmp_path / "sync-events.jsonl")
    monkeypatch.setattr(sync_tasks, "event_store", store)
    status = SyncTaskStatus(
        task_id=task_id,
        state="running",
        started_at=10.0,
        total_files=3,
        completed_files=1,
        failed_files=1,
        skipped_files=1,
        uploaded_files=1,
        last_error="boom",
        current_run_id="run-1",
        last_files=[
            SyncFileEvent(path=str(local_dir), status="started", timestamp=10.0),
            SyncFileEvent(path=str(local_dir / "a.md"), status="uploaded", timestamp=11.0),
        ],
    )
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: status})
    monkeypatch.setattr(sync_tasks.runner, "get_status", lambda _task_id: status)

    store.append(
        SyncEventRecord(
            timestamp=11.0,
            task_id=task_id,
            task_name="诊断任务",
            status="uploaded",
            path=str(local_dir / "a.md"),
            message="ok",
            run_id="run-1",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=12.0,
            task_id=task_id,
            task_name="诊断任务",
            status="failed",
            path=str(local_dir / "b.md"),
            message="boom",
            run_id="run-1",
        )
    )

    overview = tray_client.get("/sync/tasks/overview")
    assert overview.status_code == 200
    item = overview.json()[0]
    assert item["task"]["id"] == task_id
    assert item["status"]["current_run_id"] == "run-1"
    assert item["counts"]["processed"] == 3
    assert item["counts"]["uploaded"] == 1
    assert item["problem_count"] >= 1
    assert item["current_file"]["status"] == "uploaded"

    diagnostics = tray_client.get(f"/sync/tasks/{task_id}/diagnostics?limit=10")
    assert diagnostics.status_code == 200
    body = diagnostics.json()
    assert body["overview"]["task"]["id"] == task_id
    assert body["recent_events"][0]["run_id"] == "run-1"
    assert body["problems"][0]["status"] == "failed"

    by_run = tray_client.get("/sync/logs/sync?run_id=run-1")
    assert by_run.status_code == 200
    assert by_run.json()["total"] == 2


def test_sync_task_diagnostics_isolated_by_run(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.api.sync_tasks as sync_tasks

    local_dir = tmp_path / "run-local"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "运行隔离任务",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-run",
        "cloud_folder_name": "云端运行",
        "base_path": None,
        "sync_mode": "bidirectional",
        "update_mode": "auto",
        "enabled": False,
    }
    created = tray_client.post("/sync/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]

    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    persisted_runs = SyncRunService(session_maker=get_session_maker(db_url))
    monkeypatch.setattr(sync_tasks, "run_service", persisted_runs)
    store = SyncEventStore(tmp_path / "sync-events-runs.jsonl")
    monkeypatch.setattr(sync_tasks, "event_store", store)
    status = SyncTaskStatus(
        task_id=task_id,
        state="success",
        started_at=20.0,
        finished_at=25.0,
        total_files=1,
        completed_files=1,
        failed_files=0,
        skipped_files=0,
        uploaded_files=1,
        current_run_id="run-2",
        last_files=[
            SyncFileEvent(path=str(local_dir), status="started", timestamp=20.0),
            SyncFileEvent(path=str(local_dir / "new.md"), status="uploaded", timestamp=21.0),
            SyncFileEvent(path=str(local_dir), status="success", timestamp=25.0),
        ],
    )
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: status})
    monkeypatch.setattr(sync_tasks.runner, "get_status", lambda _task_id: status)
    asyncio.run(
        persisted_runs.finish_run(
            run_id="run-1",
            task_id=task_id,
            trigger_source="scheduled_upload",
            state="failed",
            started_at=10.0,
            finished_at=13.0,
            last_event_at=13.0,
            total_files=1,
            completed_files=0,
            failed_files=1,
            skipped_files=0,
            uploaded_files=0,
            downloaded_files=0,
            deleted_files=0,
            conflict_files=0,
            delete_pending_files=0,
            delete_failed_files=0,
            last_error="历史错误",
        )
    )
    asyncio.run(
        persisted_runs.finish_run(
            run_id="run-2",
            task_id=task_id,
            trigger_source="scheduled_upload",
            state="success",
            started_at=20.0,
            finished_at=25.0,
            last_event_at=25.0,
            total_files=1,
            completed_files=1,
            failed_files=0,
            skipped_files=0,
            uploaded_files=1,
            downloaded_files=0,
            deleted_files=0,
            conflict_files=0,
            delete_pending_files=0,
            delete_failed_files=0,
            last_error=None,
        )
    )

    store.append(
        SyncEventRecord(
            timestamp=10.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="started",
            path=str(local_dir),
            message="第一次运行开始",
            run_id="run-1",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=12.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="failed",
            path=str(local_dir / "old.md"),
            message="历史错误",
            run_id="run-1",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=13.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="failed",
            path=str(local_dir),
            message="完成: total=1 ok=0 failed=1 skipped=0",
            run_id="run-1",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=20.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="started",
            path=str(local_dir),
            message="第二次运行开始",
            run_id="run-2",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=21.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="uploaded",
            path=str(local_dir / "new.md"),
            message="上传成功",
            run_id="run-2",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=25.0,
            task_id=task_id,
            task_name="运行隔离任务",
            status="success",
            path=str(local_dir),
            message="完成: total=1 ok=1 failed=0 skipped=0",
            run_id="run-2",
        )
    )

    overview = tray_client.get("/sync/tasks/overview")
    assert overview.status_code == 200
    overview_item = overview.json()[0]
    assert overview_item["task"]["id"] == task_id
    assert overview_item["last_result"] == "success"
    assert overview_item["problem_count"] == 0
    assert overview_item["counts"]["uploaded"] == 1
    assert overview_item["counts"]["failed"] == 0

    diagnostics = tray_client.get(f"/sync/tasks/{task_id}/diagnostics?limit=10")
    assert diagnostics.status_code == 200
    body = diagnostics.json()
    assert [item["run_id"] for item in body["recent_runs"]] == ["run-2", "run-1"]
    assert body["selected_run"]["run_id"] == "run-2"
    assert body["selected_run"]["state"] == "success"
    assert body["recent_events"][0]["run_id"] == "run-2"
    assert body["problems"] == []

    historical = tray_client.get(f"/sync/tasks/{task_id}/diagnostics?limit=10&run_id=run-1")
    assert historical.status_code == 200
    historical_body = historical.json()
    assert historical_body["selected_run"]["run_id"] == "run-1"
    assert historical_body["selected_run"]["state"] == "failed"
    assert historical_body["problems"][0]["run_id"] == "run-1"
    assert any(item["message"] == "历史错误" for item in historical_body["problems"])


@pytest.mark.asyncio
async def test_sync_task_overview_uses_persisted_sync_runs(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.api.sync_tasks as sync_tasks

    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    persisted_runs = SyncRunService(session_maker=get_session_maker(db_url))
    monkeypatch.setattr(sync_tasks, "run_service", persisted_runs)
    monkeypatch.setattr(sync_tasks, "event_store", SyncEventStore(tmp_path / "empty-sync-events.jsonl"))

    local_dir = tmp_path / "persisted-run-local"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "持久化运行任务",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-persisted",
        "cloud_folder_name": "云端持久化",
        "base_path": None,
        "sync_mode": "bidirectional",
        "update_mode": "auto",
        "enabled": False,
    }
    created = tray_client.post("/sync/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]

    await persisted_runs.finish_run(
        run_id="run-db-1",
        task_id=task_id,
        trigger_source="scheduled_upload",
        state="failed",
        started_at=100.0,
        finished_at=120.0,
        last_event_at=121.0,
        total_files=5,
        completed_files=3,
        failed_files=2,
        skipped_files=0,
        uploaded_files=2,
        downloaded_files=1,
        deleted_files=0,
        conflict_files=1,
        delete_pending_files=0,
        delete_failed_files=1,
        last_error="db-error",
    )

    idle_status = SyncTaskStatus(task_id=task_id, state="idle")
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: idle_status})
    monkeypatch.setattr(sync_tasks.runner, "get_status", lambda _task_id: idle_status)

    overview = tray_client.get("/sync/tasks/overview")
    assert overview.status_code == 200
    item = overview.json()[0]
    assert item["last_result"] == "failed"
    assert item["problem_count"] >= 1
    assert item["counts"]["uploaded"] == 2
    assert item["counts"]["delete_failed"] == 1

    diagnostics = tray_client.get(f"/sync/tasks/{task_id}/diagnostics?limit=10")
    assert diagnostics.status_code == 200
    body = diagnostics.json()
    assert body["recent_runs"][0]["run_id"] == "run-db-1"
    assert body["selected_run"]["last_error"] == "db-error"
    assert body["selected_run"]["counts"]["conflicts"] == 1


@pytest.mark.asyncio
async def test_sync_task_diagnostics_marks_stale_persisted_running_runs_cancelled(
    tray_client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    import src.api.sync_tasks as sync_tasks

    local_dir = tmp_path / "stale-run-local"
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "中断运行任务",
        "local_path": str(local_dir),
        "cloud_folder_token": "token-stale",
        "cloud_folder_name": "云端中断",
        "base_path": None,
        "sync_mode": "bidirectional",
        "update_mode": "auto",
        "enabled": False,
    }
    created = tray_client.post("/sync/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]

    persisted_runs = SyncRunService(get_session_maker())
    await persisted_runs.start_run(
        run_id="run-stale",
        task_id=task_id,
        trigger_source="scheduled_upload",
        started_at=100.0,
    )

    idle_status = SyncTaskStatus(task_id=task_id, state="idle")
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: idle_status})
    monkeypatch.setattr(sync_tasks.runner, "get_status", lambda _task_id: idle_status)

    diagnostics = tray_client.get(f"/sync/tasks/{task_id}/diagnostics?limit=10")
    assert diagnostics.status_code == 200
    body = diagnostics.json()
    assert body["recent_runs"][0]["run_id"] == "run-stale"
    assert body["recent_runs"][0]["state"] == "cancelled"
    assert body["recent_runs"][0]["finished_at"] == 100.0
    assert "中断" in body["recent_runs"][0]["last_error"]
