from dataclasses import replace
from pathlib import Path

import pytest

from src.services.sync_task_service import SyncTaskItem, SyncTaskService, SyncTaskValidationError
from src.services.sync_path_mode import (
    PathSyncRule, effective_sync_mode, path_supports_direction,
    task_supports_direction, task_for_path, can_delete_path,
)
from src.db.session import init_db, get_session_maker


def make_task(root: Path, mode: str = "bidirectional", rules: list[dict] | None = None) -> SyncTaskItem:
    return SyncTaskItem(
        id="rules-task", name="对象同步", local_path=str(root), cloud_folder_token="root",
        cloud_folder_name=None, base_path=None, sync_mode=mode, update_mode="auto",
        enabled=True, created_at=1, updated_at=1,
        path_sync_rules=[PathSyncRule(**rule) for rule in (rules or [])],
    )


def rule(path: str, mode: str, kind: str = "folder") -> dict:
    return {"path": path, "kind": kind, "sync_mode": mode}


def test_nearest_folder_and_exact_file_override_independent_of_order(tmp_path: Path) -> None:
    rules = [rule("归档/草稿.md", "upload_only", "file"), rule("归档", "download_only"),
             rule("归档/协作", "bidirectional")]
    for ordered in (rules, list(reversed(rules))):
        task = make_task(tmp_path, rules=ordered)
        assert effective_sync_mode(task, tmp_path / "归档/新文档.md") == "download_only"
        assert effective_sync_mode(task, tmp_path / "归档/草稿.md") == "upload_only"
        assert effective_sync_mode(task, tmp_path / "归档/协作/a.md") == "bidirectional"
        assert effective_sync_mode(task, tmp_path / "归档副本/a.md") == "bidirectional"
        assert effective_sync_mode(task, tmp_path / "归档/草稿.md/child") == "download_only"


@pytest.mark.parametrize("mode,direction,expected", [
    ("download_only", "upload", False), ("download_only", "download", True),
    ("upload_only", "upload", True), ("upload_only", "download", False),
    ("bidirectional", "upload", True), ("bidirectional", "download", True),
])
def test_effective_direction(tmp_path: Path, mode: str, direction: str, expected: bool) -> None:
    task = make_task(tmp_path, rules=[rule("one.md", mode, "file")])
    assert path_supports_direction(task, tmp_path / "one.md", direction) is expected
    assert not path_supports_direction(task, tmp_path.parent / "outside.md", direction)


def test_opposite_rules_enable_task_scheduler_and_markdown_upload(tmp_path: Path) -> None:
    task = make_task(tmp_path, "download_only", [rule("one.md", "upload_only", "file")])
    task = replace(task, md_sync_mode="download_only")
    assert task_supports_direction(task, "upload")
    assert task_supports_direction(task, "download")
    effective = task_for_path(task, tmp_path / "one.md")
    assert effective.sync_mode == "upload_only"
    assert effective.md_sync_mode == "doc_only"
    assert task.md_sync_mode == "download_only"


def test_parent_delete_cannot_bypass_child_rules_or_ignored_paths(tmp_path: Path) -> None:
    task = make_task(tmp_path, rules=[rule("all/protected.md", "download_only", "file")])
    assert not can_delete_path(task, tmp_path / "all", "upload", is_directory=True)
    assert can_delete_path(task, tmp_path / "all/other.md", "upload")
    task = replace(task, ignored_subpaths=["all/private"])
    assert not can_delete_path(task, tmp_path / "all", "download", is_directory=True)


@pytest.mark.asyncio
async def test_rules_persist_update_and_clear(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{(tmp_path / 'rules.db').as_posix()}"
    await init_db(url)
    service = SyncTaskService(session_maker=get_session_maker(url), owner_open_id=None)
    created = await service.create_task(
        name="对象规则", local_path=str(tmp_path / "root"), cloud_folder_token="folder",
        base_path=None, sync_mode="download_only",
        path_sync_rules=[rule("归档\\./设计.md", "upload_only", "file")],
    )
    loaded = await service.get_task(created.id)
    assert loaded.path_sync_rules == [PathSyncRule(**rule("归档/设计.md", "upload_only", "file"))]
    await service.update_task(created.id, name="重命名")
    assert (await service.get_task(created.id)).path_sync_rules == loaded.path_sync_rules
    await service.update_task(created.id, path_sync_rules=[])
    assert (await service.get_task(created.id)).path_sync_rules == []


@pytest.mark.parametrize("rules", [
    [rule("../outside", "upload_only")], [rule("a/../outside", "upload_only")],
    [rule("/absolute", "upload_only")], [rule("C:\\docs", "upload_only")],
    [rule("\\\\server\\share", "upload_only")], [rule(".", "upload_only")],
    [rule("a", "invalid")], [rule("a", "download_only"), rule("a/", "upload_only")],
])
@pytest.mark.asyncio
async def test_invalid_rules_rejected_before_save(tmp_path: Path, rules: list[dict]) -> None:
    url = f"sqlite+aiosqlite:///{(tmp_path / 'invalid.db').as_posix()}"
    await init_db(url)
    service = SyncTaskService(session_maker=get_session_maker(url), owner_open_id=None)
    with pytest.raises(SyncTaskValidationError):
        await service.create_task(name="invalid", local_path=str(tmp_path), cloud_folder_token="f",
                                  base_path=None, sync_mode="bidirectional", path_sync_rules=rules)
    assert await service.list_tasks() == []
