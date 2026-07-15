import asyncio

from fastapi.testclient import TestClient

import src.main as main
from src.core.config import AppConfig, RuntimeProfile


class _DummyRunner:
    def __init__(self, events: list[str] | None = None) -> None:
        self._events = events

    def list_statuses(self) -> dict:
        return {}

    async def close(self) -> None:
        if self._events is not None:
            self._events.append("runner:close")


class _DummyTaskService:
    async def list_tasks(self) -> list[object]:
        return []


class _DummyConflictService:
    async def list_conflicts(self, include_resolved: bool = False) -> list[object]:
        return []


class _DummyAsyncService:
    def __init__(self, name: str, events: list[str]) -> None:
        self._name = name
        self._events = events

    async def start(self) -> None:
        self._events.append(f"{self._name}:start")

    async def stop(self) -> None:
        self._events.append(f"{self._name}:stop")


class _DummyWatcherManager:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._events.append(f"watcher:set_loop:{type(loop).__name__}")


def test_health_check() -> None:
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_snapshot_profile_blocks_local_mutation_routes() -> None:
    config = AppConfig(runtime_profile=RuntimeProfile.snapshot_test)

    assert main._runtime_mutation_denied(config, "POST", "/sync/tasks/task-1/run") is True
    assert main._runtime_mutation_denied(config, "PATCH", "/config") is True
    assert main._runtime_mutation_denied(config, "GET", "/sync/tasks") is False
    assert main._runtime_mutation_denied(config, "POST", "/system/shutdown") is False


def test_create_app_lifespan_starts_and_stops_services() -> None:
    events: list[str] = []

    async def fake_init_db() -> None:
        events.append("db:init")

    async def fake_recover_runs() -> int:
        events.append("runs:recover")
        return 2

    def fake_init_logging() -> None:
        events.append("logging:init")

    app = main.create_app(
        sync_runner_service=_DummyRunner(events),
        sync_task_service_instance=_DummyTaskService(),
        conflict_service_instance=_DummyConflictService(),
        sync_scheduler_instance=_DummyAsyncService("sync_scheduler", events),
        log_maintenance_service_instance=_DummyAsyncService("log_maintenance", events),
        update_scheduler_instance=_DummyAsyncService("update_scheduler", events),
        watcher_manager_instance=_DummyWatcherManager(events),
        init_db_fn=fake_init_db,
        recover_runs_fn=fake_recover_runs,
        init_logging_fn=fake_init_logging,
    )

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

    assert events[0] == "logging:init"
    assert events[1].startswith("watcher:set_loop:")
    assert events[2:] == [
        "db:init",
        "runs:recover",
        "log_maintenance:start",
        "sync_scheduler:start",
        "update_scheduler:start",
        "log_maintenance:stop",
        "sync_scheduler:stop",
        "update_scheduler:stop",
        "runner:close",
    ]
