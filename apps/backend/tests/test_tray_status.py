import importlib
import sys
from pathlib import Path
from typing import Generator

# 确保从任意工作目录运行 pytest 时都能找到 src 包
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient

from src.core.config import ConfigManager
from src.services.sync_event_store import SyncEventRecord, SyncEventStore
from src.services.sync_runner import SyncFileEvent, SyncTaskStatus


@pytest.fixture
def tray_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    """
    独立构建一份使用临时 SQLite 的 app，以免写入真实数据目录。
    """
    monkeypatch.setenv("LARKSYNC_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "test.db"))

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

    # /tray/status 应返回未解决冲突数量
    status = tray_client.get("/tray/status").json()
    assert status["unresolved_conflicts"] == 1

    # 解决冲突后，数量应变为 0
    resolve = tray_client.post(f"/conflicts/{conflict_id}/resolve", json={"action": "use_cloud"})
    assert resolve.status_code == 200

    status_after = tray_client.get("/tray/status").json()
    assert status_after["unresolved_conflicts"] == 0


def test_tray_status_counts_running_and_errors(
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
    assert status["tasks_running"] == 1
    assert status["last_error"] == "boom"


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
        current_run_id="run-2",
        last_files=[
            SyncFileEvent(path=str(local_dir), status="started", timestamp=20.0),
            SyncFileEvent(path=str(local_dir / "new.md"), status="uploaded", timestamp=21.0),
            SyncFileEvent(path=str(local_dir), status="success", timestamp=25.0),
        ],
    )
    monkeypatch.setattr(sync_tasks.runner, "list_statuses", lambda: {task_id: status})
    monkeypatch.setattr(sync_tasks.runner, "get_status", lambda _task_id: status)

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
