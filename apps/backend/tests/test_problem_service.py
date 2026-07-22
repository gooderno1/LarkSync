from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from src.db.models import ConflictRecord, SyncRun, SyncTask
from src.db.session import get_session_maker, init_db
from src.services.problem_service import ProblemService
from src.services.sync_event_store import SyncEventRecord
from src.services.sync_run_event_service import SyncRunEventService


async def _build_services(tmp_path):
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'problems.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    return session_maker, SyncRunEventService(session_maker), ProblemService(session_maker)


async def _insert_task(session_maker, *, task_id: str = "task-1") -> None:
    async with session_maker() as session:
        session.add(
            SyncTask(
                id=task_id,
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


@pytest.mark.asyncio
async def test_refresh_sources_deduplicates_occurrences_with_stable_fingerprint(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/videos/demo.mp4",
                message="上传失败 HTTP 503 request_id=first-random-id",
                run_id="run-1",
            ),
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="d:\\work\\marketing\\videos\\demo.mp4",
                message="上传失败 HTTP 503 request_id=second-random-id",
                run_id="run-2",
            ),
        ]
    )

    refreshed = await service.refresh_sources()
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert refreshed.events_seen == 2
    assert total == 1
    assert items[0].category == "upload"
    assert items[0].severity == "high"
    assert items[0].occurrence_count == 2
    assert items[0].object_path == "videos/demo.mp4"
    assert {action.key for action in items[0].available_actions} == {"retry_task"}

    occurrences = await service.list_occurrences(items[0].id, limit=20, offset=0)
    assert len(occurrences) == 2
    evidence = json.loads(occurrences[0].evidence_json)
    assert "request_id" not in evidence["message"].lower()
    before_latest, _ = await service.list_problems(
        state="open",
        until=15.0,
        limit=20,
        offset=0,
    )
    after_latest, _ = await service.list_problems(
        state="open",
        since=15.0,
        limit=20,
        offset=0,
    )
    assert before_latest == 0
    assert after_latest == 1


@pytest.mark.asyncio
async def test_verify_task_problem_requires_matching_object_success(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/demo.md",
                message="上传失败 HTTP 500",
                run_id="run-1",
            )
        ]
    )
    await service.refresh_sources()
    _, problems = await service.list_problems(state="open", limit=20, offset=0)
    problem = problems[0]

    first = await service.verify_problem(problem.id)
    assert first is not None
    assert first.state == "open"
    assert first.resolution_verification == "not_verified"

    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-success",
                task_id="task-1",
                state="success",
                trigger_source="manual",
                started_at=11.0,
                finished_at=12.0,
                last_event_at=12.0,
                created_at=11.0,
                updated_at=12.0,
            )
        )
        await session.commit()

    not_verified = await service.verify_problem(problem.id)
    assert not_verified is not None
    assert not_verified.state == "open"
    assert not_verified.resolution_verification == "not_verified"

    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=13.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="uploaded",
                path="D:/Work/Marketing/demo.md",
                message="上传完成",
                run_id="run-success",
            )
        ]
    )
    await service.refresh_sources()
    verified = await service.verify_problem(problem.id)
    assert verified is not None
    assert verified.state == "resolved"
    assert verified.resolution_verification == "same_object_operation_succeeded"


@pytest.mark.asyncio
async def test_action_history_tracks_waiting_and_failure_without_false_resolution(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/demo.md",
                message="本地文件被占用",
                run_id="run-1",
            )
        ]
    )
    await service.refresh_sources()
    _, problems = await service.list_problems(state="open", limit=20, offset=0)
    problem = problems[0]

    action = await service.start_action(problem.id, "retry_task")
    waiting = await service.finish_action(
        action.id,
        result="accepted",
        verification_result="waiting_for_later_run",
    )
    assert waiting.result == "accepted"
    updated = await service.get_problem(problem.id)
    assert updated is not None
    assert updated.state == "waiting"

    second = await service.start_action(problem.id, "retry_task")
    failed = await service.finish_action(
        second.id,
        result="failed",
        error_code="TASK_BUSY",
        error_message="任务仍在运行",
    )
    assert failed.result == "failed"
    reopened = await service.get_problem(problem.id)
    assert reopened is not None
    assert reopened.state == "open"
    assert reopened.resolved_at is None

    actions = await service.list_actions(problem.id, limit=20, offset=0)
    assert [item.result for item in actions] == ["failed", "accepted"]


@pytest.mark.asyncio
async def test_conflict_source_is_materialized_once_and_tracks_source_resolution(tmp_path) -> None:
    session_maker, _, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    async with session_maker() as session:
        session.add(
            ConflictRecord(
                id="conflict-1",
                local_path="D:/Work/Marketing/brief.md",
                cloud_token="doccn-sensitive-token",
                local_hash="local-hash",
                db_hash="base-hash",
                cloud_version=3,
                db_version=2,
                created_at=10.0,
                resolved=False,
            )
        )
        await session.commit()

    await service.refresh_sources()
    await service.refresh_sources()
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert total == 1
    assert items[0].category == "conflict"
    assert items[0].occurrence_count == 1
    assert {action.key for action in items[0].available_actions} == {"use_cloud", "use_local"}
    occurrence = (await service.list_occurrences(items[0].id, limit=20, offset=0))[0]
    assert json.loads(occurrence.evidence_json)["cloud_token"] == "docc***oken"

    async with session_maker() as session:
        conflict = await session.get(ConflictRecord, "conflict-1")
        assert conflict is not None
        conflict.resolved = True
        conflict.resolved_action = "use_cloud"
        conflict.resolved_at = 20.0
        await session.commit()

    await service.refresh_sources()
    resolved = await service.get_problem(items[0].id)
    assert resolved is not None
    assert resolved.state == "resolved"
    assert resolved.resolution_verification == "source_resolved"


@pytest.mark.asyncio
async def test_same_object_success_resolves_problem_and_new_failure_reopens_it(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/demo.md",
                message="上传失败 HTTP 503",
                run_id="run-1",
            ),
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="uploaded",
                path="D:/Work/Marketing/demo.md",
                message="上传完成",
                run_id="run-2",
            ),
        ]
    )

    await service.backfill_sources(batch_size=10)
    total, resolved_items = await service.list_problems(state="resolved", limit=20, offset=0)

    assert total == 1
    assert resolved_items[0].resolution_verification == "same_object_operation_succeeded"
    assert resolved_items[0].resolved_by_run_id == "run-2"
    assert resolved_items[0].last_good_at == 20.0

    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=30.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/demo.md",
                message="上传失败 HTTP 503",
                run_id="run-3",
            )
        ]
    )
    await service.refresh_sources()
    reopened = await service.get_problem(resolved_items[0].id)

    assert reopened is not None
    assert reopened.state == "open"
    assert reopened.resolution_verification == "reopened_by_occurrence"
    assert reopened.resolved_by_run_id is None


@pytest.mark.asyncio
async def test_success_for_different_object_does_not_resolve_problem(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/a.md",
                message="上传失败 HTTP 503",
                run_id="run-1",
            ),
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="uploaded",
                path="D:/Work/Marketing/b.md",
                message="上传完成",
                run_id="run-2",
            ),
        ]
    )

    await service.backfill_sources(batch_size=10)
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert total == 1
    assert items[0].object_path == "a.md"


@pytest.mark.asyncio
async def test_delete_pending_is_workflow_state_not_problem(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="delete_pending",
                path="D:/Work/Marketing/old.md",
                message="进入安全删除宽限期",
                run_id="run-1",
            )
        ]
    )

    refreshed = await service.refresh_sources()
    total, _ = await service.list_problems(state="open", limit=20, offset=0)

    assert refreshed.events_seen == 0
    assert total == 0
