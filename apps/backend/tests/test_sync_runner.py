from pathlib import Path

import pytest

from src.services.drive_service import DriveNode
from src.services.file_writer import FileWriter
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_runner import SyncTaskRunner, _merge_synced_link_map, _parse_mtime
from src.services.sync_task_service import SyncTaskItem
from src.services.watcher import FileChangeEvent


class FakeDriveService:
    def __init__(self, tree: DriveNode) -> None:
        self._tree = tree
        self.calls: list[tuple[str, str | None]] = []

    async def scan_folder(self, folder_token: str, name: str | None = None) -> DriveNode:
        self.calls.append((folder_token, name))
        return self._tree

    async def close(self) -> None:
        return None


class FakeDocxService:
    async def list_blocks(self, document_id: str, user_id_type: str = "open_id"):
        return []

    async def close(self) -> None:
        return None


class FakeTranscoder:
    async def to_markdown(
        self,
        document_id: str,
        blocks: list[dict],
        *,
        base_dir=None,
        link_map=None,
    ) -> str:
        return f"# {document_id}"

    async def close(self) -> None:
        return None


class FakeFileDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def download(self, file_token: str, file_name: str, target_dir: Path, mtime: float):
        self.calls.append((file_token, file_name))
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / file_name
        path.write_bytes(b"data")

    async def close(self) -> None:
        return None


class FakeFileUploader:
    async def close(self) -> None:
        return None


class FakeImportTaskService:
    async def close(self) -> None:
        return None


class FakeLinkService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    async def upsert_link(
        self, local_path: str, cloud_token: str, cloud_type: str, task_id: str, updated_at=None
    ):
        self.calls.append((local_path, cloud_token, cloud_type, task_id))
        return None

    async def get_by_local_path(self, local_path: str):
        return None

    async def list_all(self):
        return []


@pytest.mark.asyncio
async def test_runner_downloads_docx_and_files(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="doc-1",
                name="设计文档",
                type="docx",
                modified_time="1700000000000",
            ),
            DriveNode(
                token="file-1",
                name="spec.pdf",
                type="file",
                modified_time="1700000000",
            ),
            DriveNode(
                token="folder-1",
                name="子目录",
                type="folder",
                children=[
                    DriveNode(
                        token="doc-2",
                        name="note.docx",
                        type="docx",
                        modified_time="1700000000",
                    )
                ],
            ),
            DriveNode(
                token="sheet-1",
                name="表格",
                type="sheet",
                modified_time="1700000000",
            ),
            DriveNode(
                token="shortcut-1",
                name="快捷方式文件",
                type="shortcut",
                shortcut_info={
                    "target_token": "file-target",
                    "target_type": "file",
                },
                modified_time="1700000000",
            ),
        ],
    )

    downloader = FakeFileDownloader()
    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=downloader,
        file_writer=FileWriter(),
        link_service=FakeLinkService(),
    )

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        base_path=None,
        sync_mode="download_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    await runner.run_task(task)

    status = runner.get_status(task.id)
    assert status.total_files == 5
    assert status.completed_files == 4
    assert status.skipped_files == 1
    assert status.failed_files == 0
    assert status.state == "success"

    assert (tmp_path / "设计文档.md").exists()
    assert (tmp_path / "spec.pdf").exists()
    assert (tmp_path / "子目录" / "note.md").exists()
    assert (tmp_path / "快捷方式文件").exists()
    assert downloader.calls[-1][0] == "file-target"


def test_parse_mtime_supports_iso8601() -> None:
    ts = _parse_mtime("2025-01-02T03:04:05Z")
    assert abs(ts - 1735787045) < 1.0


def test_parse_mtime_supports_ms_string() -> None:
    assert _parse_mtime("1700000000000") == 1700000000.0


def test_merge_synced_link_map_only_uses_existing_paths(tmp_path: Path) -> None:
    tree_target = tmp_path / "tree.md"
    tree_target.write_text("# tree", encoding="utf-8")
    synced_target = tmp_path / "external.md"
    synced_target.write_text("# external", encoding="utf-8")
    missing_target = tmp_path / "missing.md"

    merged = _merge_synced_link_map(
        {"doccn-in-tree": tree_target},
        [
            SyncLinkItem(
                local_path=str(synced_target),
                cloud_token="doccn-external",
                cloud_type="docx",
                task_id="task-a",
                updated_at=0.0,
            ),
            SyncLinkItem(
                local_path=str(missing_target),
                cloud_token="doccn-missing",
                cloud_type="docx",
                task_id="task-a",
                updated_at=0.0,
            ),
            SyncLinkItem(
                local_path=str(tmp_path / "override.md"),
                cloud_token="doccn-in-tree",
                cloud_type="docx",
                task_id="task-a",
                updated_at=0.0,
            ),
        ],
    )

    assert merged["doccn-in-tree"] == tree_target
    assert merged["doccn-external"] == synced_target
    assert "doccn-missing" not in merged


@pytest.mark.asyncio
async def test_handle_local_event_calls_upload_with_all_dependencies(tmp_path: Path) -> None:
    tree = DriveNode(token="root", name="root", type="folder")
    drive_service = FakeDriveService(tree)
    file_uploader = FakeFileUploader()
    import_task_service = FakeImportTaskService()
    runner = SyncTaskRunner(
        drive_service=drive_service,
        docx_service=FakeDocxService(),
        file_uploader=file_uploader,
        import_task_service=import_task_service,
        link_service=FakeLinkService(),
    )
    task = SyncTaskItem(
        id="task-evt",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    path = tmp_path / "demo.md"
    path.write_text("# demo", encoding="utf-8")
    event = FileChangeEvent(
        event_type="modified",
        src_path=str(path),
        dest_path=None,
        timestamp=0.0,
    )
    captured: dict[str, tuple] = {}

    async def _capture_upload_path(*args):
        captured["args"] = args

    runner._upload_path = _capture_upload_path  # type: ignore[method-assign]

    await runner._handle_local_event(task, event)

    assert "args" in captured
    assert len(captured["args"]) == 7
    assert captured["args"][0] is task
    assert captured["args"][2] == path
    assert captured["args"][5] is drive_service
    assert captured["args"][6] is import_task_service
