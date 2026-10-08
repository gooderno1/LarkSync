from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.sync_path_mode import PathSyncRule
from src.services.sync_runner import SyncTaskRunner, SyncTaskStatus
from src.services.sync_scheduler import _should_upload, _should_download
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_delete_sync_service import SyncDeleteSyncService
from src.services.watcher import FileChangeEvent
from src.services.drive_service import DriveNode
from src.services.sync_download_support_service import DownloadCandidate
from test_sync_path_mode import make_task, rule


def make_runner() -> SyncTaskRunner:
    runner = SyncTaskRunner()
    runner._record_event = lambda status, event, *args: status.record_event(event)
    return runner


@pytest.mark.parametrize("mode,override,direction", [
    ("download_only", "upload_only", "upload"),
    ("upload_only", "download_only", "download"),
])
def test_scheduler_includes_opposite_rule(tmp_path: Path, mode, override, direction) -> None:
    task = make_task(tmp_path, mode, [rule("a", override)])
    assert _should_upload(task) and _should_download(task)
    assert not _should_upload(replace(task, enabled=False))
    assert not _should_download(replace(task, enabled=False))


@pytest.mark.asyncio
async def test_upload_guard_applies_to_forced_upload_and_uses_effective_mode(tmp_path: Path) -> None:
    path = tmp_path / "one.md"
    path.write_text("# local", encoding="utf-8")
    runner = make_runner()
    runner._path_upload_service._upload_markdown = AsyncMock()
    runner._path_upload_service._record_event = runner._record_event
    task = make_task(tmp_path, rules=[rule("one.md", "download_only", "file")])
    status = SyncTaskStatus(task_id=task.id)
    await runner._upload_path(task, status, path, None, None, None, None, force=True)
    runner._path_upload_service._upload_markdown.assert_not_awaited()
    assert status.skipped_files == 1
    task = replace(task, sync_mode="download_only", md_sync_mode="download_only",
                   path_sync_rules=[PathSyncRule(**rule("one.md", "upload_only", "file"))])
    await runner._upload_path(task, status, path, None, None, None, None)
    effective = runner._path_upload_service._upload_markdown.await_args.args[0]
    assert effective.sync_mode == "upload_only"
    assert effective.md_sync_mode == "doc_only"


@pytest.mark.asyncio
async def test_watcher_only_queues_upload_enabled_paths_and_moved_children(tmp_path: Path) -> None:
    runner = make_runner()
    task = make_task(tmp_path, "download_only", [rule("drafts", "upload_only")])
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts/a.md").write_text("a", encoding="utf-8")
    await runner._handle_local_event(task, FileChangeEvent(
        event_type="modified", src_path=str(tmp_path / "keep.md"), dest_path=None, is_directory=False, timestamp=1,
    ))
    assert not runner._pending_uploads
    await runner._handle_local_event(task, FileChangeEvent(
        event_type="moved", src_path=str(tmp_path / "old"), dest_path=str(tmp_path / "drafts"),
        is_directory=True, timestamp=2,
    ))
    assert set(runner._pending_uploads[task.id]) == {str(tmp_path / "drafts/a.md")}


@pytest.mark.asyncio
async def test_manual_run_and_first_reconciliation_use_both_effective_directions(tmp_path: Path) -> None:
    task = make_task(tmp_path, "download_only", [rule("draft.md", "upload_only", "file")])
    runner = make_runner()
    runner._run_download = AsyncMock()
    runner._run_upload = AsyncMock()
    runner._finalize_run_status = AsyncMock()
    await runner.run_task(task)
    runner._run_download.assert_awaited_once()
    runner._run_upload.assert_awaited_once()
    runner._task_service = SimpleNamespace()
    runner._run_download.reset_mock()
    runner._run_upload_paths = AsyncMock()
    (tmp_path / "draft.md").write_text("draft", encoding="utf-8")
    (tmp_path / "cloud.md").write_text("cloud", encoding="utf-8")
    await runner._run_additive_reconciliation_if_needed(task, SyncTaskStatus(task_id=task.id))
    assert runner._run_download.await_args.kwargs["allow_deletes"] is False
    assert runner._run_upload_paths.await_args.args[2] == [tmp_path / "draft.md"]


def test_download_local_newer_check_uses_object_direction(tmp_path: Path) -> None:
    path = tmp_path / "one.md"
    path.write_text("local", encoding="utf-8")
    runner = make_runner()
    task = make_task(tmp_path, rules=[rule("one.md", "download_only", "file")])
    assert not runner._should_skip_download_for_local_newer(task=task, local_path=path, cloud_mtime=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["upload_only", "download_only"])
async def test_forced_download_obeys_rules_and_download_only_never_writes_mirror(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "one.md"
    task = replace(make_task(tmp_path, rules=[rule("one.md", mode, "file")]), md_sync_mode="doc_and_md")
    runner = make_runner()
    service = runner._download_orchestration_service
    service._download_docx = AsyncMock(return_value="# cloud")
    service._rebuild_block_state = AsyncMock()
    service._sync_markdown_mirror_copy = AsyncMock()
    service._record_event = runner._record_event
    runtime = SimpleNamespace(docx_service=None, transcoder=None, file_uploader=None, drive_service=None,
                              link_service=SimpleNamespace(upsert_link=AsyncMock()))
    candidate = DownloadCandidate(
        node=DriveNode(token="doc", name="one", type="docx"), relative_dir=Path("."),
        effective_token="doc", effective_type="docx", target_dir=tmp_path, target_path=path, mtime=1,
    )
    await service._download_candidate(task=task, status=SyncTaskStatus(task_id=task.id), candidate=candidate,
                                      runtime=runtime, persisted=None, link_map={}, force_paths={str(path)},
                                      allow_cloud_writes=True)
    service._sync_markdown_mirror_copy.assert_not_awaited()
    service._rebuild_block_state.assert_not_awaited()
    if mode == "upload_only":
        service._download_docx.assert_not_awaited()
        assert not path.exists()
    else:
        assert path.read_text(encoding="utf-8") == "# cloud"
        assert path.stat().st_mtime == 1
        runtime.link_service.upsert_link.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("direction,mode", [("upload", "download_only"), ("download", "upload_only")])
async def test_conflict_resolution_cannot_override_direction_rules(tmp_path: Path, direction: str, mode: str) -> None:
    runner = make_runner()
    task = make_task(tmp_path, rules=[rule("one.md", mode, "file")])
    with pytest.raises(ValueError, match="当前对象同步规则禁止"):
        if direction == "upload":
            await runner.run_conflict_upload(task, tmp_path / "one.md")
        else:
            await runner.run_conflict_download(task, tmp_path / "one.md", "doc")


@pytest.mark.asyncio
async def test_cloud_folder_mapping_does_not_create_upload_only_directories(tmp_path: Path) -> None:
    runner = make_runner()
    runner._link_service = SimpleNamespace(upsert_link=AsyncMock())
    task = make_task(tmp_path, rules=[rule("drafts", "upload_only"), rule("drafts/reference", "download_only")])
    await runner._sync_cloud_folder_links(task, [
        (DriveNode(token="drafts", name="drafts", type="folder"), Path("drafts")),
        (DriveNode(token="archive", name="archive", type="folder"), Path("archive")),
    ])
    assert not (tmp_path / "drafts").exists()
    assert (tmp_path / "archive").is_dir()
    assert runner._link_service.upsert_link.await_count == 2
    await runner._sync_cloud_folder_links(task, [
        (DriveNode(token="reference", name="reference", type="folder"), Path("drafts/reference")),
    ])
    assert (tmp_path / "drafts/reference").is_dir()


def delete_service(links: list[SyncLinkItem], pending=None):
    tombstones = SimpleNamespace(
        create_or_refresh=AsyncMock(return_value=SimpleNamespace(created=True)),
        list_pending=AsyncMock(return_value=pending or []), mark_status=AsyncMock(),
    )
    service = SyncDeleteSyncService(
        link_service=SimpleNamespace(list_by_task=AsyncMock(return_value=links),
                                     get_by_local_path=AsyncMock(return_value=links[0] if links else None)),
        tombstone_service=tombstones, block_service=SimpleNamespace(),
        should_ignore_path=lambda task, path: False, local_trash_dir_name=".trash",
    )
    return service, tombstones


@pytest.mark.asyncio
@pytest.mark.parametrize("source,mode", [("local", "download_only"), ("cloud", "upload_only")])
async def test_delete_detection_and_old_tombstones_respect_current_rule(tmp_path: Path, source, mode) -> None:
    path = tmp_path / "one.md"
    task = make_task(tmp_path, rules=[rule("one.md", mode, "file")])
    link = SyncLinkItem(local_path=str(path), cloud_token="doc", cloud_type="docx", task_id=task.id, updated_at=1)
    pending = SimpleNamespace(id="tb", local_path=str(path), cloud_token="doc", cloud_type="docx", source=source)
    service, tombstones = delete_service([link], [pending])
    status = SyncTaskStatus(task_id=task.id)
    if source == "local":
        await service.enqueue_local_delete_tombstone(task=task, status=status, local_path=path,
                                                    reason="delete", record_event=lambda *args: None)
        await service.enqueue_missing_local_deletes(task=task, status=status, record_event=lambda *args: None)
    else:
        await service.enqueue_cloud_missing_deletes(task=task, status=status, persisted_links=[link],
                                                    cloud_paths=set(), record_event=lambda *args: None)
    tombstones.create_or_refresh.assert_not_awaited()
    drive = SimpleNamespace(delete_file=AsyncMock())
    cleanup = AsyncMock()
    await service.process_pending_deletes(task=task, status=status, drive_service=drive,
                                          record_event=lambda *args: None, cleanup_md_mirror_copy=cleanup,
                                          silence_path=lambda *args, **kwargs: None)
    drive.delete_file.assert_not_awaited()
    cleanup.assert_not_awaited()
    assert tombstones.mark_status.await_args.kwargs["status"] == "cancelled"


@pytest.mark.asyncio
async def test_parent_folder_delete_keeps_protected_child_but_allows_other_files(tmp_path: Path) -> None:
    task = make_task(tmp_path, rules=[rule("all/keep.md", "download_only", "file")])
    links = [SyncLinkItem(local_path=str(tmp_path / path), cloud_token=path, cloud_type=kind,
                          task_id=task.id, updated_at=1)
             for path, kind in [("all", "folder"), ("all/keep.md", "docx"), ("all/drop.md", "docx")]]
    service, tombstones = delete_service(links)
    await service.enqueue_missing_local_deletes(task=task, status=SyncTaskStatus(task_id=task.id),
                                                record_event=lambda *args: None)
    assert [call.kwargs["local_path"] for call in tombstones.create_or_refresh.await_args_list] == [str(tmp_path / "all/drop.md")]
