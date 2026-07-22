from __future__ import annotations

from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.problems import router
from src.db.models import SyncTask
from src.db.session import get_session_maker, init_db
from src.services.problem_service import ProblemService
from src.services.sync_event_store import SyncEventRecord
from src.services.sync_run_event_service import SyncRunEventService


class _TaskService:
    async def get_task(self, task_id: str):
        if task_id != "task-1":
            return None
        return SimpleNamespace(id=task_id, local_path="D:/Work/Marketing")


class _Runner:
    def __init__(self) -> None:
        self.started: list[str] = []

    def start_task(self, task) -> None:
        self.started.append(task.id)


@pytest.mark.asyncio
async def test_problem_api_lists_details_and_executes_real_task_action(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-1",
                name="市场资料备份",
                local_path="D:/Work/Marketing",
                cloud_folder_token="folder-token",
                sync_mode="bidirectional",
                update_mode="auto",
                md_sync_mode="enhanced",
                owner_device_id="device",
                is_test=True,
                enabled=True,
                created_at=1.0,
                updated_at=1.0,
            )
        )
        await session.commit()
    await SyncRunEventService(session_maker).append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/demo.md",
                message="上传失败 HTTP 503 request_id=private",
                run_id="run-1",
            )
        ]
    )
    problem_service = ProblemService(session_maker)
    await problem_service.refresh_sources()

    app = FastAPI()
    app.include_router(router)
    runner = _Runner()
    app.state.problem_service = problem_service
    app.state.sync_task_service = _TaskService()
    app.state.sync_runner = runner
    app.state.conflict_service = object()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        refresh_mock = AsyncMock(side_effect=AssertionError("GET 不应触发问题回填"))
        problem_service.refresh_sources = refresh_mock  # type: ignore[method-assign]
        response = await client.get("/problems")
        assert response.status_code == 200
        refresh_mock.assert_not_awaited()
        payload = response.json()
        assert payload["total"] == 1
        problem = payload["items"][0]
        assert problem["category"] == "upload"
        assert [item["key"] for item in problem["available_actions"]] == [
            "retry_task",
        ]

        detail_response = await client.get(f"/problems/{problem['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["history"]["occurrences"][0]["evidence"]["message"] == (
            "上传失败 HTTP 503 请求标识已脱敏"
        )

        action_response = await client.post(
            f"/problems/{problem['id']}/actions",
            json={"action_key": "retry_task"},
        )
        assert action_response.status_code == 200
        assert action_response.json()["verification_result"] == "waiting_for_later_run"
        assert runner.started == ["task-1"]

        summary_response = await client.get("/problems/summary")
        assert summary_response.status_code == 200
        refresh_mock.assert_not_awaited()
        assert summary_response.json()["by_state"]["waiting"] == 1
