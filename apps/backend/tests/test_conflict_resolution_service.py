from pathlib import Path

import pytest

from src.db.session import get_session_maker, init_db
from src.services.conflict_resolution_service import (
    ConflictResolutionError,
    ConflictResolutionService,
)
from src.services.conflict_service import ConflictService
from src.services.sync_task_service import SyncTaskItem


class FakeLink:
    def __init__(self, *, task_id: str) -> None:
        self.task_id = task_id


class FakeLinkService:
    def __init__(self, links: dict[str, FakeLink] | None = None) -> None:
        self._links = links or {}

    async def get_by_local_path(self, local_path: str):
        return self._links.get(local_path)


class FakeTaskService:
    def __init__(self, tasks: dict[str, SyncTaskItem]) -> None:
        self._tasks = tasks

    async def get_task(self, task_id: str):
        return self._tasks.get(task_id)

    async def list_tasks(self):
        return list(self._tasks.values())


class FakeRunner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.upload_calls: list[tuple[str, str]] = []
        self.download_calls: list[tuple[str, str, str]] = []

    async def run_conflict_upload(self, task: SyncTaskItem, path: Path):
        self.upload_calls.append((task.id, str(path)))
        if self.fail:
            raise RuntimeError("upload failed")

    async def run_conflict_download(
        self, task: SyncTaskItem, path: Path, cloud_token: str
    ):
        self.download_calls.append((task.id, str(path), cloud_token))
        if self.fail:
            raise RuntimeError("download failed")


def _build_task(local_root: Path) -> SyncTaskItem:
    return SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=str(local_root),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0.0,
        updated_at=0.0,
    )


@pytest.mark.asyncio
async def test_resolve_use_local_runs_runner_and_marks_conflict_resolved(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    conflict_service = ConflictService(session_maker=get_session_maker(db_url))
    local_root = tmp_path / "docs"
    local_root.mkdir()
    local_path = local_root / "a.md"
    local_path.write_text("# local", encoding="utf-8")
    item = await conflict_service.add_conflict(
        local_path=str(local_path),
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    task = _build_task(local_root)
    runner = FakeRunner()
    resolver = ConflictResolutionService(
        conflict_service=conflict_service,
        task_service=FakeTaskService({task.id: task}),
        link_service=FakeLinkService({str(local_path): FakeLink(task_id=task.id)}),
    )

    resolved = await resolver.resolve_conflict(item.id, "use_local", runner=runner)

    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.resolved_action == "use_local"
    assert runner.upload_calls == [(task.id, str(local_path))]
    assert runner.download_calls == []


@pytest.mark.asyncio
async def test_resolve_use_cloud_by_parent_task_path_when_link_missing(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    conflict_service = ConflictService(session_maker=get_session_maker(db_url))
    local_root = tmp_path / "docs"
    local_root.mkdir()
    local_path = local_root / "nested" / "a.md"
    local_path.parent.mkdir()
    local_path.write_text("# cloud", encoding="utf-8")
    item = await conflict_service.add_conflict(
        local_path=str(local_path),
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    task = _build_task(local_root)
    runner = FakeRunner()
    resolver = ConflictResolutionService(
        conflict_service=conflict_service,
        task_service=FakeTaskService({task.id: task}),
        link_service=FakeLinkService(),
    )

    resolved = await resolver.resolve_conflict(item.id, "use_cloud", runner=runner)

    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.resolved_action == "use_cloud"
    assert runner.upload_calls == []
    assert runner.download_calls == [(task.id, str(local_path), "docx123")]


@pytest.mark.asyncio
async def test_resolve_keeps_conflict_unresolved_when_runner_fails(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    conflict_service = ConflictService(session_maker=get_session_maker(db_url))
    local_root = tmp_path / "docs"
    local_root.mkdir()
    local_path = local_root / "a.md"
    local_path.write_text("# local", encoding="utf-8")
    item = await conflict_service.add_conflict(
        local_path=str(local_path),
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    task = _build_task(local_root)
    resolver = ConflictResolutionService(
        conflict_service=conflict_service,
        task_service=FakeTaskService({task.id: task}),
        link_service=FakeLinkService({str(local_path): FakeLink(task_id=task.id)}),
    )

    with pytest.raises(ConflictResolutionError):
        await resolver.resolve_conflict(
            item.id,
            "use_local",
            runner=FakeRunner(fail=True),
        )

    current = await conflict_service.get_conflict(item.id)
    assert current is not None
    assert current.resolved is False
    assert current.resolved_action is None
