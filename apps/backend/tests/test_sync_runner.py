import os
from pathlib import Path

import pytest

from src.services.drive_service import DriveNode
from src.services.file_writer import FileWriter
from src.services.export_task_service import ExportTaskCreateResult, ExportTaskResult
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
        self.export_calls: list[tuple[str, str]] = []

    async def download(self, file_token: str, file_name: str, target_dir: Path, mtime: float):
        self.calls.append((file_token, file_name))
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / file_name
        path.write_bytes(b"data")

    async def download_exported_file(
        self, file_token: str, file_name: str, target_dir: Path, mtime: float
    ):
        self.export_calls.append((file_token, file_name))
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / file_name
        path.write_bytes(b"exported")

    async def close(self) -> None:
        return None


class FakeFileUploader:
    async def close(self) -> None:
        return None


class FakeImportTaskService:
    async def close(self) -> None:
        return None


class FakeExportTaskService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, str, str]] = []
        self.query_calls: list[tuple[str, str | None]] = []

    async def create_export_task(self, *, file_extension: str, file_token: str, file_type: str):
        self.create_calls.append((file_extension, file_token, file_type))
        return ExportTaskCreateResult(ticket="ticket-1")

    async def get_export_task_result(self, ticket: str, *, file_token: str | None = None):
        self.query_calls.append((ticket, file_token))
        return ExportTaskResult(
            file_extension="xlsx",
            type="sheet",
            file_name="表格.xlsx",
            file_token="export-file",
            file_size=10,
            job_status=0,
            job_error_msg=None,
        )

    async def close(self) -> None:
        return None


class FakeLinkService:
    def __init__(self, persisted: list[SyncLinkItem] | None = None) -> None:
        self.calls: list[tuple[str, str, str, str]] = []
        self._persisted = persisted or []

    async def upsert_link(
        self, local_path: str, cloud_token: str, cloud_type: str, task_id: str, updated_at=None
    ):
        self.calls.append((local_path, cloud_token, cloud_type, task_id))
        return None

    async def get_by_local_path(self, local_path: str):
        return None

    async def list_all(self):
        return list(self._persisted)


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
                token="slides-1",
                name="路演幻灯片",
                type="slides",
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
        export_task_service=FakeExportTaskService(),
    )

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="download_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    await runner.run_task(task)

    status = runner.get_status(task.id)
    assert status.total_files == 6
    assert status.completed_files == 6
    assert status.skipped_files == 0
    assert status.failed_files == 0
    assert status.state == "success"

    assert (tmp_path / "设计文档.md").exists()
    assert (tmp_path / "spec.pdf").exists()
    assert (tmp_path / "表格.xlsx").exists()
    assert (tmp_path / "路演幻灯片.pptx").exists()
    assert (tmp_path / "子目录" / "note.md").exists()
    assert (tmp_path / "快捷方式文件").exists()
    assert downloader.calls[-1][0] == "file-target"


@pytest.mark.asyncio
async def test_runner_download_prefers_persisted_link_when_cloud_has_duplicates(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="doc-old",
                name="重复文档",
                type="docx",
                modified_time="1700000000",
            ),
            DriveNode(
                token="doc-new",
                name="重复文档",
                type="docx",
                modified_time="1800000000",
            ),
        ],
    )
    local_path = tmp_path / "重复文档.md"
    persisted_link = SyncLinkItem(
        local_path=str(local_path),
        cloud_token="doc-old",
        cloud_type="docx",
        task_id="task-dup",
        updated_at=0.0,
    )
    link_service = FakeLinkService([persisted_link])
    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=link_service,
    )

    task = SyncTaskItem(
        id="task-dup",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="download_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    await runner.run_task(task)

    assert local_path.read_text(encoding="utf-8") == "# doc-old"
    assert any(call[1] == "doc-old" for call in link_service.calls)


@pytest.mark.asyncio
async def test_bidirectional_skips_download_when_local_file_is_newer(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="doc-1",
                name="设计文档",
                type="docx",
                modified_time="1000",
            )
        ],
    )
    local_file = tmp_path / "设计文档.md"
    local_file.write_text("# local newer", encoding="utf-8")
    os.utime(local_file, (2000.0, 2000.0))

    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(),
    )

    task = SyncTaskItem(
        id="task-2",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = runner.get_status(task.id)
    await runner._run_download(task, status)

    assert local_file.read_text(encoding="utf-8") == "# local newer"
    assert status.total_files == 1
    assert status.completed_files == 0
    assert status.skipped_files == 1
    assert status.last_files[-1].message == "本地较新，跳过下载"


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
async def test_runner_sanitizes_invalid_names(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="folder-1",
                name="项目:资料",
                type="folder",
                children=[
                    DriveNode(
                        token="doc-1",
                        name='报告 "A"',
                        type="docx",
                        modified_time="1700000000",
                    ),
                    DriveNode(
                        token="file-1",
                        name="data:2026.csv",
                        type="file",
                        modified_time="1700000000",
                    ),
                ],
            )
        ],
    )

    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(),
    )

    task = SyncTaskItem(
        id="task-sanitize",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="download_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    await runner.run_task(task)

    assert (tmp_path / "项目_资料" / "报告 _A_.md").exists()
    assert (tmp_path / "项目_资料" / "data_2026.csv").exists()


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
        cloud_folder_name=None,
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

    pending = runner._pending_uploads.get(task.id)
    assert pending is not None
    assert str(path) in pending
    status = runner.get_status(task.id)
    assert status.last_files[-1].status == "queued"
