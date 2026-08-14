from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from src.db.models import (
    ConflictRecord,
    ProblemOccurrence,
    ProblemRecord,
    SyncMeta,
    SyncRun,
    SyncRunEvent,
    SyncTask,
    SyncTaskCheckState,
)
from src.db.session import get_session_maker, init_db
from src.services.problem_service import ProblemService
from src.services.sync_event_store import SyncEventRecord
from src.services.sync_run_event_service import SyncRunEventService


async def _build_services(tmp_path):
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'problems.db').as_posix()}"
    await init_db(db_url)
    session_maker = get_session_maker(db_url)
    return (
        session_maker,
        SyncRunEventService(session_maker),
        ProblemService(session_maker, ignore_hidden_cache_paths=True),
    )


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
async def test_refresh_sources_separates_upload_object_from_failed_run_summary(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-upload",
                task_id="task-1",
                state="failed",
                trigger_source="scheduled_upload",
                started_at=10.0,
                finished_at=12.0,
                last_event_at=12.0,
                created_at=10.0,
                updated_at=12.0,
            )
        )
        await session.commit()
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=11.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/src/resource/package_marker",
                message="文件大小不能为空",
                run_id="run-upload",
            ),
            SyncEventRecord(
                timestamp=12.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="完成: total=1 ok=0 failed=1 skipped=0",
                run_id="run-upload",
            ),
        ]
    )

    await service.refresh_sources()
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert total == 1
    assert items[0].category == "upload"
    assert items[0].object_kind == "sync_object"
    assert items[0].object_path == "src/resource/package_marker"


@pytest.mark.asyncio
async def test_zero_count_failed_run_summary_is_not_a_download_problem(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-auth-preflight",
                task_id="task-1",
                state="failed",
                trigger_source="scheduled_download",
                started_at=10.0,
                finished_at=12.0,
                last_event_at=12.0,
                last_error="refresh token is invalid, it may has been used (code=20026)",
                created_at=10.0,
                updated_at=12.0,
            )
        )
        await session.commit()
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=11.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="refresh token is invalid, it may has been used (code=20026)",
                run_id="run-auth-preflight",
            ),
            SyncEventRecord(
                timestamp=12.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="完成: total=0 ok=0 failed=0 skipped=0",
                run_id="run-auth-preflight",
            ),
        ]
    )

    await service.refresh_sources()
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert total == 1
    assert items[0].category == "auth_permission"
    assert items[0].operation_family == "task_auth"
    assert items[0].object_kind == "task_run"
    assert items[0].occurrence_count == 1


@pytest.mark.asyncio
async def test_refresh_sources_resolves_legacy_failed_run_summary_problem(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-summary",
                task_id="task-1",
                state="failed",
                trigger_source="scheduled_upload",
                started_at=10.0,
                finished_at=12.0,
                last_event_at=12.0,
                created_at=10.0,
                updated_at=12.0,
            )
        )
        await session.commit()
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=12.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="完成: total=1 ok=0 failed=1 skipped=0",
                run_id="run-summary",
            )
        ]
    )
    async with session_maker() as session:
        event = (
            await session.execute(
                select(SyncRunEvent).where(SyncRunEvent.run_id == "run-summary")
            )
        ).scalar_one()
        session.add(
            ProblemRecord(
                id="legacy-summary",
                fingerprint="legacy-summary-fingerprint",
                category="system",
                severity="medium",
                state="open",
                title="同步失败 · Marketing",
                summary="同步动作未完成，需要查看原始证据。",
                task_id="task-1",
                object_kind="sync_event",
                object_key="marketing",
                object_path="Marketing",
                first_seen_at=12.0,
                last_seen_at=12.0,
                occurrence_count=1,
                latest_run_id="run-summary",
                latest_event_id=event.id,
                classifier_version="problem-classifier-v2",
                actionability="diagnostic_only",
            )
        )
        await session.commit()

    await service.refresh_sources()
    item = await service.get_problem("legacy-summary")

    assert item is not None
    assert item.state == "resolved"
    assert item.object_kind == "task_run"
    assert item.resolution_verification == "workflow_summary_not_problem"


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", ["open", "ignored"])
async def test_refresh_sources_resolves_current_classifier_failed_run_summary_problem(
    tmp_path,
    initial_state: str,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=12.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="完成: total=0 ok=0 failed=0 skipped=0",
                run_id="run-current-summary",
            )
        ]
    )
    async with session_maker() as session:
        event = (
            await session.execute(
                select(SyncRunEvent).where(
                    SyncRunEvent.run_id == "run-current-summary"
                )
            )
        ).scalar_one()
        session.add(
            ProblemRecord(
                id="current-summary",
                fingerprint="current-summary-fingerprint",
                category="download",
                severity="medium",
                state=initial_state,
                title="下载失败 · Marketing",
                summary="文件或文档内容没有成功同步到本地。",
                task_id="task-1",
                object_kind="task_run",
                object_key="marketing",
                object_path="Marketing",
                first_seen_at=12.0,
                last_seen_at=12.0,
                occurrence_count=1,
                latest_run_id="run-current-summary",
                latest_event_id=event.id,
                classifier_version="problem-classifier-v3",
                actionability="auto_recovering",
                ignored_reason=(
                    "历史问题暂时忽略" if initial_state == "ignored" else None
                ),
                ignored_at=12.0 if initial_state == "ignored" else None,
            )
        )
        await session.commit()

    await service.refresh_sources()
    item = await service.get_problem("current-summary")

    assert item is not None
    assert item.state == "resolved"
    assert item.object_kind == "task_run"
    assert item.resolution_verification == "workflow_summary_not_problem"
    assert item.actionability == "diagnostic_only"
    assert item.ignored_reason is None
    assert item.ignored_at is None


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
async def test_manual_ignore_and_restore_are_audited_without_false_resolution(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/legacy.md",
                message="上传失败 HTTP 503",
                run_id="run-1",
            )
        ]
    )
    await service.refresh_sources()
    _, problems = await service.list_problems(state="open", limit=20, offset=0)
    problem = problems[0]

    ignored = await service.ignore_problem(problem.id, "历史问题，当前无需处理")

    assert ignored.state == "ignored"
    assert ignored.ignored_reason == "历史问题，当前无需处理"
    assert ignored.ignored_at is not None
    assert ignored.resolved_at is None
    assert ignored.resolution_verification == "manually_ignored"
    assert (await service.get_summary())["unresolved"] == 0
    with pytest.raises(ValueError, match="cannot be ignored"):
        await service.ignore_problem(problem.id, "重复操作")

    restored = await service.restore_problem(problem.id)

    assert restored.state == "open"
    assert restored.ignored_reason is None
    assert restored.ignored_at is None
    assert restored.resolution_verification == "manually_restored"
    actions = await service.list_actions(problem.id, limit=20, offset=0)
    assert [item.action_key for item in actions] == ["restore_problem", "ignore_problem"]
    assert all(item.result == "accepted" for item in actions)
    with pytest.raises(ValueError, match="not ignored"):
        await service.restore_problem(problem.id)


@pytest.mark.asyncio
async def test_ignored_problem_stays_ignored_on_failure_but_resolves_on_matching_success(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/legacy.md",
                message="上传失败 HTTP 503",
                run_id="run-1",
            )
        ]
    )
    await service.refresh_sources()
    _, problems = await service.list_problems(state="open", limit=20, offset=0)
    problem = await service.ignore_problem(problems[0].id, "外部条件限制，暂时接受")

    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/legacy.md",
                message="上传失败 HTTP 503",
                run_id="run-2",
            )
        ]
    )
    await service.refresh_sources()
    repeated = await service.get_problem(problem.id)

    assert repeated is not None
    assert repeated.state == "ignored"
    assert repeated.occurrence_count == 2
    assert repeated.ignored_reason == "外部条件限制，暂时接受"

    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=30.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="uploaded",
                path="D:/Work/Marketing/legacy.md",
                message="上传完成",
                run_id="run-3",
            )
        ]
    )
    await service.refresh_sources()
    resolved = await service.get_problem(problem.id)

    assert resolved is not None
    assert resolved.state == "resolved"
    assert resolved.ignored_reason is None
    assert resolved.ignored_at is None
    assert resolved.resolution_verification == "same_object_operation_succeeded"


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


@pytest.mark.asyncio
async def test_reconcile_current_state_resolves_obsolete_upload_but_keeps_live_error(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    task_root = tmp_path / "sync-root"
    task_root.mkdir()
    existing = task_root / "still-failing.md"
    existing.write_text("content", encoding="utf-8")
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-current-state",
                name="当前状态收敛",
                local_path=task_root.as_posix(),
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
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-current-state",
                task_name="当前状态收敛",
                status="failed",
                path=(task_root / "removed.md").as_posix(),
                message="上传失败 HTTP 500",
                run_id="run-removed",
            ),
            SyncEventRecord(
                timestamp=11.0,
                task_id="task-current-state",
                task_name="当前状态收敛",
                status="failed",
                path=existing.as_posix(),
                message="上传失败 HTTP 500",
                run_id="run-existing",
            ),
        ]
    )
    await service.refresh_sources()

    result = await service.reconcile_current_state(batch_size=20, max_batches=1)
    open_total, open_items = await service.list_problems(state="open", limit=20, offset=0)
    resolved_total, resolved_items = await service.list_problems(
        state="resolved",
        limit=20,
        offset=0,
    )

    assert result.resolved == 1
    assert open_total == 1
    assert open_items[0].object_path == "still-failing.md"
    assert resolved_total == 1
    assert resolved_items[0].object_path == "removed.md"
    assert resolved_items[0].resolution_verification == "target_absent_verified"


@pytest.mark.asyncio
async def test_reconcile_current_state_keeps_error_when_task_root_is_unavailable(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    unavailable_root = tmp_path / "disconnected-drive"
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-unavailable",
                name="不可用同步根目录",
                local_path=unavailable_root.as_posix(),
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
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-unavailable",
                task_name="不可用同步根目录",
                status="failed",
                path=(unavailable_root / "document.md").as_posix(),
                message="上传失败 HTTP 500",
                run_id="run-unavailable",
            )
        ]
    )
    await service.refresh_sources()

    result = await service.reconcile_current_state(batch_size=20, max_batches=1)
    open_total, _ = await service.list_problems(state="open", limit=20, offset=0)

    assert result.resolved == 0
    assert open_total == 1


@pytest.mark.asyncio
async def test_reconcile_current_state_uses_current_ignore_and_task_recovery(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    task_root = tmp_path / "sync-root"
    ignored = task_root / "__pycache__" / "module.pyc"
    ignored.parent.mkdir(parents=True)
    ignored.write_bytes(b"cache")
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-recovered",
                name="恢复证据",
                local_path=task_root.as_posix(),
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
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-recovered",
                task_name="恢复证据",
                status="failed",
                path=ignored.as_posix(),
                message="上传失败 HTTP 500",
                run_id="run-ignored",
            ),
            SyncEventRecord(
                timestamp=11.0,
                task_id="task-recovered",
                task_name="恢复证据",
                status="failed",
                path=task_root.as_posix(),
                message="OAuth 授权过期 401",
                run_id="run-auth",
            ),
            SyncEventRecord(
                timestamp=12.0,
                task_id="task-recovered",
                task_name="恢复证据",
                status="cancelled",
                path=task_root.as_posix(),
                message="应用退出",
                run_id="run-cancelled",
            ),
        ]
    )
    await service.refresh_sources()
    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-later-success",
                task_id="task-recovered",
                state="success",
                trigger_source="scheduled_upload",
                started_at=19.0,
                finished_at=20.0,
                last_event_at=20.0,
                uploaded_files=1,
                run_kind="activity",
                has_activity=True,
                created_at=19.0,
                updated_at=20.0,
            )
        )
        await session.commit()

    result = await service.reconcile_current_state(batch_size=20, max_batches=1)
    total, resolved = await service.list_problems(state="resolved", limit=20, offset=0)

    assert result.resolved == 3
    assert total == 3
    assert {item.resolution_verification for item in resolved} == {
        "path_excluded",
        "task_auth_recovered",
        "later_run_succeeded",
    }
    recovered = next(item for item in resolved if item.category == "auth_permission")
    assert recovered.resolved_by_run_id == "run-later-success"


@pytest.mark.asyncio
async def test_reconcile_task_download_failure_requires_later_download_success(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    task_root = tmp_path / "sync-root"
    task_root.mkdir()
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-directional-recovery",
                name="任务方向恢复",
                local_path=task_root.as_posix(),
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
        session.add(
            SyncRun(
                run_id="run-download-failed",
                task_id="task-directional-recovery",
                state="failed",
                trigger_source="scheduled_download",
                started_at=9.0,
                finished_at=10.0,
                last_event_at=10.0,
                last_error="获取文件清单失败: unknown error.",
                run_kind="activity",
                has_activity=True,
                created_at=9.0,
                updated_at=10.0,
            )
        )
        session.add(
            SyncRun(
                run_id="run-upload-success",
                task_id="task-directional-recovery",
                state="success",
                trigger_source="scheduled_upload",
                started_at=19.0,
                finished_at=20.0,
                last_event_at=20.0,
                run_kind="legacy_check",
                has_activity=False,
                created_at=19.0,
                updated_at=20.0,
            )
        )
        await session.commit()
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-directional-recovery",
                task_name="任务方向恢复",
                status="failed",
                path=task_root.as_posix(),
                message="获取文件清单失败: unknown error.",
                run_id="run-download-failed",
            )
        ]
    )
    await service.refresh_sources()

    first = await service.reconcile_current_state(batch_size=20, max_batches=1)
    open_total, open_items = await service.list_problems(
        state="open", limit=20, offset=0
    )

    assert first.resolved == 0
    assert open_total == 1
    assert open_items[0].object_kind == "task_run"
    assert open_items[0].operation_family == "download"

    async with session_maker() as session:
        session.add(
            SyncRun(
                run_id="run-download-success",
                task_id="task-directional-recovery",
                state="success",
                trigger_source="scheduled_download",
                started_at=29.0,
                finished_at=30.0,
                last_event_at=30.0,
                total_files=640,
                skipped_files=640,
                run_kind="legacy_check",
                has_activity=False,
                created_at=29.0,
                updated_at=30.0,
            )
        )
        await session.commit()

    second = await service.reconcile_current_state(batch_size=20, max_batches=1)
    resolved_total, resolved_items = await service.list_problems(
        state="resolved", limit=20, offset=0
    )

    assert second.resolved == 1
    assert resolved_total == 1
    assert resolved_items[0].resolution_verification == "later_matching_run_succeeded"
    assert resolved_items[0].resolved_by_run_id == "run-download-success"


@pytest.mark.asyncio
async def test_reconcile_task_download_failure_uses_later_directional_no_change_check(
    tmp_path,
) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    task_root = tmp_path / "sync-root"
    task_root.mkdir()
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-check-recovery",
                name="检测事实恢复",
                local_path=task_root.as_posix(),
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
        session.add(
            SyncTaskCheckState(
                task_id="task-check-recovery",
                direction="upload",
                state="no_change",
                trigger_source="scheduled_upload",
                started_at=19.0,
                finished_at=20.0,
                change_count=0,
                consecutive_no_change=1,
                updated_at=20.0,
            )
        )
        await session.commit()
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-check-recovery",
                task_name="检测事实恢复",
                status="failed",
                path=task_root.as_posix(),
                message="获取文件清单失败: unknown error.",
                run_id="run-download-failed",
            )
        ]
    )
    await service.refresh_sources()

    upload_only = await service.reconcile_current_state(batch_size=20, max_batches=1)
    open_total, _ = await service.list_problems(state="open", limit=20, offset=0)

    assert upload_only.resolved == 0
    assert open_total == 1

    async with session_maker() as session:
        session.add(
            SyncTaskCheckState(
                task_id="task-check-recovery",
                direction="download",
                state="no_change",
                trigger_source="scheduled_download",
                started_at=29.0,
                finished_at=30.0,
                change_count=0,
                consecutive_no_change=1,
                updated_at=30.0,
            )
        )
        await session.commit()

    result = await service.reconcile_current_state(batch_size=20, max_batches=1)
    total, items = await service.list_problems(state="resolved", limit=20, offset=0)

    assert result.resolved == 1
    assert total == 1
    assert items[0].resolution_verification == "later_matching_check_succeeded"
    assert items[0].resolved_by_run_id is None


@pytest.mark.asyncio
async def test_reconcile_current_state_resolves_missing_local_io_object(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    task_root = tmp_path / "sync-root"
    task_root.mkdir()
    missing = task_root / "moved.md"
    async with session_maker() as session:
        session.add(
            SyncTask(
                id="task-local-move",
                name="本地移动收敛",
                local_path=task_root.as_posix(),
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
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-local-move",
                task_name="本地移动收敛",
                status="failed",
                path=missing.as_posix(),
                message="[WinError 2] 系统找不到指定的文件。",
                run_id="run-moved",
            )
        ]
    )
    await service.refresh_sources()

    result = await service.reconcile_current_state(batch_size=20, max_batches=1)
    resolved_total, resolved_items = await service.list_problems(
        state="resolved", limit=20, offset=0
    )

    assert result.resolved == 1
    assert resolved_total == 1
    assert resolved_items[0].category == "local_io"
    assert resolved_items[0].resolution_verification == "target_absent_verified"


@pytest.mark.asyncio
async def test_refresh_sources_recounts_legacy_summary_occurrences(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="完成: total=0 ok=0 failed=0 skipped=0",
                run_id="run-summary",
            ),
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing",
                message="获取文件清单失败: internal error",
                run_id="run-real-error",
            ),
        ]
    )
    async with session_maker() as session:
        problem = ProblemRecord(
            id="legacy-mixed-problem",
            fingerprint="legacy-mixed-fingerprint",
            category="download",
            severity="medium",
            state="open",
            title="下载失败 · Marketing",
            summary="云端内容没有成功写入本地。",
            task_id="task-1",
            object_kind="task_run",
            object_key="d:/work/marketing",
            object_path="D:/Work/Marketing",
            first_seen_at=10.0,
            last_seen_at=20.0,
            occurrence_count=2,
            latest_run_id="run-real-error",
            latest_event_id="legacy-real-event",
            classifier_version="problem-classifier-v3",
            operation_family="download",
            actionability="auto_recovering",
        )
        session.add(problem)
        session.add_all(
            [
                ProblemOccurrence(
                    id="legacy-summary-occurrence",
                    problem_id=problem.id,
                    source_kind="sync_event",
                    source_id="legacy-summary-event",
                    run_id="run-summary",
                    event_id="legacy-summary-event",
                    occurred_at=10.0,
                    evidence_json="{}",
                ),
                ProblemOccurrence(
                    id="legacy-real-occurrence",
                    problem_id=problem.id,
                    source_kind="sync_event",
                    source_id="legacy-real-event",
                    run_id="run-real-error",
                    event_id="legacy-real-event",
                    occurred_at=20.0,
                    evidence_json="{}",
                ),
            ]
        )
        summary_event = await session.get(SyncRunEvent, "legacy-summary-event")
        real_event = await session.get(SyncRunEvent, "legacy-real-event")
        assert summary_event is None
        assert real_event is None
        session.add_all(
            [
                SyncRunEvent(
                    id="legacy-summary-event",
                    task_id="task-1",
                    task_name="市场资料备份",
                    run_id="run-summary",
                    timestamp=10.0,
                    status="failed",
                    path="D:/Work/Marketing",
                    message="完成: total=0 ok=0 failed=0 skipped=0",
                    created_at=10.0,
                ),
                SyncRunEvent(
                    id="legacy-real-event",
                    task_id="task-1",
                    task_name="市场资料备份",
                    run_id="run-real-error",
                    timestamp=20.0,
                    status="failed",
                    path="D:/Work/Marketing",
                    message="获取文件清单失败: internal error",
                    created_at=20.0,
                ),
            ]
        )
        await session.commit()

    await service.refresh_sources(event_limit=1)
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert total == 1
    assert items[0].occurrence_count == 1


@pytest.mark.asyncio
async def test_refresh_sources_advances_a_persistent_cursor_in_bounded_batches(tmp_path) -> None:
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

    first = await service.refresh_sources(event_limit=1)
    total_open, _ = await service.list_problems(state="open", limit=20, offset=0)
    async with session_maker() as session:
        cursor = await session.get(SyncMeta, "problem_event_cursor_v4")

    assert first.events_seen == 1
    assert total_open == 1
    assert cursor is not None
    assert '"timestamp": 10.0' in (cursor.value or "")

    second = await service.refresh_sources(event_limit=1)
    total_resolved, resolved = await service.list_problems(
        state="resolved",
        limit=20,
        offset=0,
    )

    assert second.events_seen == 1
    assert total_resolved == 1
    assert resolved[0].resolution_verification == "same_object_operation_succeeded"


@pytest.mark.asyncio
async def test_initialize_live_cursor_fast_forwards_without_losing_history_checkpoint(tmp_path) -> None:
    session_maker, event_service, service = await _build_services(tmp_path)
    await _insert_task(session_maker)
    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=10.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/old.md",
                message="旧上传失败",
                run_id="run-old",
            ),
            SyncEventRecord(
                timestamp=20.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="uploaded",
                path="D:/Work/Marketing/old.md",
                message="旧上传完成",
                run_id="run-old-recovered",
            ),
        ]
    )
    legacy_value = '{"timestamp": 10.0, "event_id": "legacy-event"}'
    async with session_maker() as session:
        session.add(
            SyncMeta(
                key="problem_event_cursor_v3",
                value=legacy_value,
                updated_at=10.0,
            )
        )
        await session.commit()

    initialized = await service.initialize_live_cursor()
    async with session_maker() as session:
        live = await session.get(SyncMeta, "problem_event_cursor_v4")
        legacy = await session.get(SyncMeta, "problem_event_cursor_v3")
        history = await session.get(SyncMeta, "problem_history_cursor_v3")

    assert initialized is True
    assert live is not None and '"timestamp": 20.0' in (live.value or "")
    assert legacy is not None and legacy.value == legacy_value
    assert history is not None and history.value == legacy_value

    await event_service.append_batch(
        [
            SyncEventRecord(
                timestamp=30.0,
                task_id="task-1",
                task_name="市场资料备份",
                status="failed",
                path="D:/Work/Marketing/new.md",
                message="新上传失败 HTTP 503",
                run_id="run-new",
            )
        ]
    )
    initialized_again = await service.initialize_live_cursor()
    refreshed = await service.refresh_sources(event_limit=20)
    total, items = await service.list_problems(state="open", limit=20, offset=0)

    assert initialized_again is False
    assert refreshed.events_seen == 1
    assert total == 1
    assert items[0].object_path == "new.md"
