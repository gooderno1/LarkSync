from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from src.core.account_context import account_scope, current_account_id
from src.db.models import (
    LEGACY_ACCOUNT_ID, ConflictRecord, ProblemOccurrence, ProblemRecord,
    ProblemRecoveryFact, SyncLink, SyncRunEvent, SyncTask,
)
from src.db.session import get_session_maker, init_db
from src.services.problem_file_verification_service import ProblemFileVerificationService
from src.services.problem_service import ProblemService


CONTENT = b"already synchronized Word file"
DIGEST = hashlib.sha256(CONTENT).hexdigest()


class FakeDownloader:
    def __init__(self, *, matches=True, error=None, during_download=None):
        self.matches = matches
        self.error = error
        self.during_download = during_download
        self.calls = []
        self.closed = False

    async def matches_file(self, token, *, expected_hash, expected_size):
        self.calls.append((current_account_id(), token, expected_hash, expected_size))
        if self.error:
            raise self.error
        if self.during_download:
            await self.during_download()
        return self.matches

    async def close(self):
        self.closed = True


async def _setup(tmp_path, *, downloader=None, account_id=LEGACY_ACCOUNT_ID):
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'verification.db').as_posix()}"
    await init_db(db_url)
    sessions = get_session_maker(db_url)
    path = tmp_path / "招聘.docx"
    path.write_bytes(CONTENT)
    key = ProblemService.build_resolution_key(
        task_id="task-1", object_key=path.name.lower(), operation_family="upload",
    )
    async with sessions() as session:
        session.add_all([
            SyncTask(
                id="task-1", account_id=account_id, name="宁怡科技",
                local_path=str(tmp_path), cloud_folder_token="folder",
                sync_mode="bidirectional", update_mode="auto", enabled=True,
                created_at=1.0, updated_at=1.0,
            ),
            SyncLink(
                account_id=account_id, local_path=str(path), task_id="task-1",
                cloud_token="cloud-word", cloud_type="file", updated_at=1.0,
                local_hash=DIGEST, local_size=len(CONTENT),
                local_mtime=path.stat().st_mtime,
            ),
            ProblemRecord(
                id="problem-1", account_id=account_id, fingerprint="fingerprint-1",
                category="upload", severity="high", state="waiting",
                title="上传失败", summary="MemoryError()", task_id="task-1",
                object_kind="sync_object", object_key=path.name.lower(),
                object_path=path.name, first_seen_at=10.0, last_seen_at=10.0,
                occurrence_count=1, latest_event_id="original-failure",
                classifier_version="problem-classifier-v3", resolution_key=key,
                operation_family="upload", actionability="auto_recovering",
                resolution_verification="waiting_for_later_run",
            ),
            ProblemOccurrence(
                id="occurrence-1", account_id=account_id, problem_id="problem-1",
                source_kind="sync_event", source_id="original-failure",
                occurred_at=10.0, evidence_json='{"message":"MemoryError()"}',
            ),
        ])
        await session.commit()
    downloader = downloader or FakeDownloader()
    service = ProblemFileVerificationService(
        sessions, downloader_factory=lambda: downloader, ignore_hidden_cache_paths=True,
    )
    return sessions, path, downloader, service


async def _problem(sessions):
    async with sessions() as session:
        return await session.get(ProblemRecord, "problem-1")


@pytest.mark.asyncio
async def test_verified_unchanged_file_closes_old_waiting_problem_with_audit(tmp_path):
    sessions, path, downloader, service = await _setup(tmp_path, account_id="account-b")

    result = await service.reconcile()

    assert result.resolved == 1
    problem = await _problem(sessions)
    assert problem.state == "resolved"
    assert problem.resolution_verification == "same_object_content_verified"
    assert problem.occurrence_count == 1
    assert problem.latest_event_id == "original-failure"
    assert downloader.calls == [("account-b", "cloud-word", DIGEST, len(CONTENT))]
    assert downloader.closed
    assert current_account_id() is None
    assert path.read_bytes() == CONTENT
    async with sessions() as session:
        event = await session.get(SyncRunEvent, problem.resolved_by_event_id)
        fact = await session.get(ProblemRecoveryFact, problem.resolved_by_event_id)
        assert event.status == "upload_verified"
        assert event.account_id == "account-b"
        assert event.timestamp > problem.last_seen_at
        evidence = json.loads(event.message)
        assert evidence["sha256"] == DIGEST
        assert evidence["size"] == len(CONTENT)
        assert fact.account_id == "account-b"
        assert fact.operation_family == "upload"
        assert fact.resolution_key == problem.resolution_key
        assert await session.get(ProblemOccurrence, "occurrence-1") is not None
    assert (await service.reconcile()).resolved == 0
    assert len(downloader.calls) == 1
    with account_scope("account-b"):
        verified = await ProblemService(sessions).verify_problem("problem-1")
        assert verified.resolution_verification == "same_object_content_verified"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["different", "network_error"])
async def test_cloud_mismatch_or_failure_keeps_problem(tmp_path, outcome):
    downloader = FakeDownloader(
        matches=outcome != "different",
        error=RuntimeError("HTTP 503") if outcome == "network_error" else None,
    )
    sessions, _, _, service = await _setup(tmp_path, downloader=downloader)

    assert (await service.reconcile()).resolved == 0
    assert (await _problem(sessions)).state == "waiting"
    assert downloader.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", [
    "local_changed", "no_baseline_hash", "no_baseline_size", "wrong_link_task",
    "wrong_link_account", "not_binary", "download_problem", "conflict_problem",
    "task_problem", "disabled_task", "download_only", "path_download_only",
    "ignored_path", "out_of_root", "pending_conflict", "conflict_other_token",
])
async def test_unverified_or_unrelated_objects_never_close(tmp_path, condition):
    sessions, path, downloader, service = await _setup(tmp_path)
    async with sessions() as session:
        problem = await session.get(ProblemRecord, "problem-1")
        task = await session.get(SyncTask, "task-1")
        link = await session.get(SyncLink, (LEGACY_ACCOUNT_ID, str(path)))
        if condition == "local_changed":
            path.write_bytes(b"new unsynchronized content")
        elif condition == "no_baseline_hash":
            link.local_hash = None
        elif condition == "no_baseline_size":
            link.local_size = None
        elif condition == "wrong_link_task":
            link.task_id = "another-task"
        elif condition == "wrong_link_account":
            link.account_id = "another-account"
        elif condition == "not_binary":
            link.cloud_type = "docx"
        elif condition == "download_problem":
            problem.operation_family = "download"
        elif condition == "conflict_problem":
            problem.object_kind = "conflict"
        elif condition == "task_problem":
            problem.object_kind = "task_run"
        elif condition == "disabled_task":
            task.enabled = False
        elif condition == "download_only":
            task.sync_mode = "download_only"
        elif condition == "path_download_only":
            task.path_sync_rules = json.dumps([
                {"path": path.name, "kind": "file", "sync_mode": "download_only"},
            ])
        elif condition == "ignored_path":
            task.ignored_subpaths = json.dumps([path.name])
        elif condition == "out_of_root":
            problem.object_path = "../outside.docx"
        elif condition == "pending_conflict":
            session.add(_conflict(path))
        elif condition == "conflict_other_token":
            conflict = _conflict(path)
            conflict.cloud_token = "older-cloud-token"
            session.add(conflict)
        await session.commit()

    assert (await service.reconcile()).resolved == 0
    assert (await _problem(sessions)).state == "waiting"
    assert downloader.calls == []


def _conflict(path):
    return ConflictRecord(
        id="conflict-1", account_id=LEGACY_ACCOUNT_ID, local_path=str(path),
        cloud_token="cloud-word", local_hash=DIGEST, db_hash=DIGEST,
        cloud_version=2, db_version=1, created_at=20.0, resolved=False,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["file", "failure", "link", "rule", "conflict"])
async def test_changes_during_cloud_verification_invalidate_evidence(tmp_path, change):
    sessions, path, downloader, service = await _setup(tmp_path)

    async def mutate():
        async with sessions() as session:
            if change == "file":
                path.write_bytes(b"modified during verification")
            elif change == "failure":
                problem = await session.get(ProblemRecord, "problem-1")
                problem.last_seen_at = 30.0
                problem.occurrence_count = 2
            elif change == "link":
                link = await session.get(SyncLink, (LEGACY_ACCOUNT_ID, str(path)))
                link.cloud_token = "replacement-token"
            elif change == "rule":
                task = await session.get(SyncTask, "task-1")
                task.sync_mode = "download_only"
            elif change == "conflict":
                session.add(_conflict(path))
            await session.commit()

    downloader.during_download = mutate

    assert (await service.reconcile()).resolved == 0
    assert (await _problem(sessions)).state == "waiting"
    async with sessions() as session:
        assert (await session.execute(select(ProblemRecoveryFact))).scalars().all() == []


@pytest.mark.asyncio
async def test_other_file_conflict_is_preserved_without_blocking_verified_file(tmp_path):
    sessions, path, _, service = await _setup(tmp_path)
    async with sessions() as session:
        session.add(_conflict(path.with_name("另一个文件.md")))
        await session.commit()

    assert (await service.reconcile()).resolved == 1
    async with sessions() as session:
        assert not (await session.get(ConflictRecord, "conflict-1")).resolved
