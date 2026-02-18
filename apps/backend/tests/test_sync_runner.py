import os
import time
from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.services.drive_service import DriveFile, DriveFileList, DriveNode
from src.services.file_writer import FileWriter
from src.services.export_task_service import (
    ExportTaskCreateResult,
    ExportTaskError,
    ExportTaskResult,
)
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


class FakeTombstoneService:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.pending: list[dict] = []
        self.marked: list[tuple[str, str, str | None, float | None]] = []

    async def create_or_refresh(self, **kwargs):
        self.created.append(kwargs)
        item = {
            "id": f"tb-{len(self.created)}",
            "task_id": kwargs["task_id"],
            "local_path": kwargs["local_path"],
            "cloud_token": kwargs.get("cloud_token"),
            "cloud_type": kwargs.get("cloud_type"),
            "source": kwargs["source"],
            "status": "pending",
            "reason": kwargs.get("reason"),
            "detected_at": time.time(),
            "expire_at": kwargs["expire_at"],
            "executed_at": None,
        }
        self.pending.append(item)
        return item

    async def list_pending(self, task_id: str, *, before: float | None = None):
        entries = [
            item
            for item in self.pending
            if item["task_id"] == task_id and item.get("status") in {"pending", "failed"}
        ]
        if before is not None:
            entries = [item for item in entries if item["expire_at"] <= before]
        result = []
        for item in entries:
            result.append(
                type(
                    "Pending",
                    (),
                    item,
                )()
            )
        return result

    async def mark_status(
        self,
        tombstone_id: str,
        *,
        status: str,
        reason: str | None = None,
        expire_at: float | None = None,
    ):
        self.marked.append((tombstone_id, status, reason, expire_at))
        updated: list[dict] = []
        for item in self.pending:
            if item["id"] != tombstone_id:
                updated.append(item)
                continue
            item["status"] = status
            if reason is not None:
                item["reason"] = reason
            if expire_at is not None:
                item["expire_at"] = expire_at
            if status in {"executed", "cancelled"}:
                continue
            updated.append(item)
        self.pending = updated
        return True


class FakeExportTaskService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, str, str, str | None]] = []
        self.query_calls: list[tuple[str, str | None]] = []

    async def create_export_task(
        self,
        *,
        file_extension: str,
        file_token: str,
        file_type: str,
        sub_id: str | None = None,
    ):
        self.create_calls.append((file_extension, file_token, file_type, sub_id))
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


class FakeSheetService:
    def __init__(self, sheet_ids: list[str] | None = None) -> None:
        self.sheet_ids = sheet_ids or []
        self.calls: list[str] = []

    async def list_sheet_ids(self, spreadsheet_token: str) -> list[str]:
        self.calls.append(spreadsheet_token)
        return list(self.sheet_ids)

    async def close(self) -> None:
        return None


class FakeLinkService:
    def __init__(self, persisted: list[SyncLinkItem] | None = None) -> None:
        self.calls: list[tuple[str, str, str, str, str | None]] = []
        self._persisted = persisted or []

    async def upsert_link(
        self,
        local_path: str,
        cloud_token: str,
        cloud_type: str,
        task_id: str,
        updated_at=None,
        cloud_parent_token: str | None = None,
        **kwargs,
    ):
        self.calls.append((local_path, cloud_token, cloud_type, task_id, cloud_parent_token))
        return None

    async def get_by_local_path(self, local_path: str):
        for item in self._persisted:
            if item.local_path == local_path:
                return item
        return None

    async def list_all(self):
        return list(self._persisted)

    async def list_by_task(self, task_id: str):
        return [item for item in self._persisted if item.task_id == task_id]

    async def delete_by_local_path(self, local_path: str):
        before = len(self._persisted)
        self._persisted = [item for item in self._persisted if item.local_path != local_path]
        return before != len(self._persisted)


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
    assert status.total_files == 5
    assert status.completed_files == 5
    assert status.skipped_files == 0
    assert status.failed_files == 0
    assert status.state == "success"

    assert (tmp_path / "设计文档.md").exists()
    assert (tmp_path / "spec.pdf").exists()
    assert (tmp_path / "表格.xlsx").exists()
    assert (tmp_path / "子目录" / "note.md").exists()
    assert (tmp_path / "快捷方式文件").exists()
    assert downloader.calls[-1][0] == "file-target"


@pytest.mark.asyncio
async def test_runner_download_skips_internal_md_mirror_folder(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="doc-main",
                name="主文档",
                type="docx",
                modified_time="1700000000",
            ),
            DriveNode(
                token="folder-md-mirror",
                name="_LarkSync_MD_Mirror",
                type="folder",
                children=[
                    DriveNode(
                        token="doc-shadow",
                        name="镜像文档",
                        type="docx",
                        modified_time="1700000000",
                    )
                ],
            ),
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
        id="task-skip-md-mirror",
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
    assert status.total_files == 1
    assert status.completed_files == 1
    assert (tmp_path / "主文档.md").exists()
    assert not (tmp_path / "_LarkSync_MD_Mirror").exists()


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
async def test_runner_skips_unchanged_when_persisted(tmp_path: Path) -> None:
    cloud_mtime = 1700000000
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="file-1",
                name="report.pdf",
                type="file",
                modified_time=str(cloud_mtime),
            )
        ],
    )

    local_path = tmp_path / "report.pdf"
    local_path.write_bytes(b"cached")

    persisted = [
        SyncLinkItem(
            local_path=str(local_path),
            cloud_token="file-1",
            cloud_type="file",
            task_id="task-unchanged",
            updated_at=float(cloud_mtime),
        )
    ]

    downloader = FakeFileDownloader()
    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=downloader,
        file_writer=FileWriter(),
        link_service=FakeLinkService(persisted),
        export_task_service=FakeExportTaskService(),
    )

    task = SyncTaskItem(
        id="task-unchanged",
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
    assert status.total_files == 1
    assert status.skipped_files == 1
    assert status.completed_files == 0
    assert downloader.calls == []


@pytest.mark.asyncio
async def test_runner_redownloads_docx_when_legacy_sheet_placeholder_present(
    tmp_path: Path,
) -> None:
    cloud_mtime = 1700000000
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="doc-legacy",
                name="历史文档",
                type="docx",
                modified_time=str(cloud_mtime),
            )
        ],
    )

    local_path = tmp_path / "历史文档.md"
    local_path.write_text("阶段清单（sheet_token: legacy_sheet_token）", encoding="utf-8")

    persisted = [
        SyncLinkItem(
            local_path=str(local_path),
            cloud_token="doc-legacy",
            cloud_type="docx",
            task_id="task-legacy",
            updated_at=float(cloud_mtime),
        )
    ]

    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(persisted),
        export_task_service=FakeExportTaskService(),
    )

    task = SyncTaskItem(
        id="task-legacy",
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
    assert status.total_files == 1
    assert status.skipped_files == 0
    assert status.completed_files == 1
    assert local_path.read_text(encoding="utf-8") == "# doc-legacy"


@pytest.mark.asyncio
async def test_runner_export_retries_with_sub_id(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="bitable-1",
                name="项目表",
                type="bitable",
                url="https://example.feishu.cn/base/abc?table=tbl123",
                modified_time="1700000000",
            )
        ],
    )

    class RetryExportTaskService(FakeExportTaskService):
        async def create_export_task(
            self,
            *,
            file_extension: str,
            file_token: str,
            file_type: str,
            sub_id: str | None = None,
        ):
            self.create_calls.append((file_extension, file_token, file_type, sub_id))
            if sub_id is None:
                raise ExportTaskError("missing sub_id")
            return ExportTaskCreateResult(ticket="ticket-1")

    export_service = RetryExportTaskService()
    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(),
        export_task_service=export_service,
    )

    task = SyncTaskItem(
        id="task-subid",
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
    assert status.failed_files == 0
    assert (tmp_path / "项目表.xlsx").exists()
    assert export_service.create_calls[0][3] is None
    assert export_service.create_calls[1][3] == "tbl123"


@pytest.mark.asyncio
async def test_export_poll_allows_processing_status_2(tmp_path: Path) -> None:
    class SlowExportTaskService(FakeExportTaskService):
        def __init__(self) -> None:
            super().__init__()
            self._calls = 0

        async def get_export_task_result(self, ticket: str, *, file_token: str | None = None):
            self.query_calls.append((ticket, file_token))
            self._calls += 1
            if self._calls < 3:
                return ExportTaskResult(
                    file_extension="xlsx",
                    type="sheet",
                    file_name="表格.xlsx",
                    file_token=None,
                    file_size=None,
                    job_status=2,
                    job_error_msg=None,
                )
            return ExportTaskResult(
                file_extension="xlsx",
                type="sheet",
                file_name="表格.xlsx",
                file_token="exported-token",
                file_size=10,
                job_status=0,
                job_error_msg=None,
            )

    downloader = FakeFileDownloader()
    export_service = SlowExportTaskService()
    runner = SyncTaskRunner(
        export_task_service=export_service,
        file_downloader=downloader,
        export_poll_interval=0,
    )

    await runner._download_exported_file(
        export_task_service=export_service,
        file_downloader=downloader,
        file_token="sheet-1",
        file_type="sheet",
        target_path=tmp_path / "表格.xlsx",
        mtime=0.0,
        export_extension="xlsx",
        export_sub_id=None,
    )

    assert (tmp_path / "表格.xlsx").exists()
    assert downloader.export_calls[0][0] == "exported-token"
    assert export_service.query_calls[-1][0] == "ticket-1"


@pytest.mark.asyncio
async def test_export_poll_raises_on_error_status() -> None:
    class FailedExportTaskService(FakeExportTaskService):
        async def get_export_task_result(self, ticket: str, *, file_token: str | None = None):
            self.query_calls.append((ticket, file_token))
            return ExportTaskResult(
                file_extension="xlsx",
                type="sheet",
                file_name="表格.xlsx",
                file_token=None,
                file_size=None,
                job_status=1,
                job_error_msg="permission denied",
            )

    export_service = FailedExportTaskService()
    runner = SyncTaskRunner(export_task_service=export_service, export_poll_attempts=1)

    with pytest.raises(RuntimeError) as exc:
        await runner._wait_for_export_task(
            export_task_service=export_service,
            ticket="ticket-err",
            file_token="sheet-err",
        )

    assert "导出任务失败" in str(exc.value)


@pytest.mark.asyncio
async def test_runner_fills_sheet_sub_id_when_missing(tmp_path: Path) -> None:
    tree = DriveNode(
        token="root",
        name="根目录",
        type="folder",
        children=[
            DriveNode(
                token="sheet-1",
                name="预算表",
                type="sheet",
                modified_time="1700000000",
            )
        ],
    )

    class DriveWithMeta(FakeDriveService):
        async def batch_query_metas(self, docs, *, with_url=True):  # type: ignore[override]
            return {}

    class RequireSubIdExportTaskService(FakeExportTaskService):
        async def create_export_task(
            self,
            *,
            file_extension: str,
            file_token: str,
            file_type: str,
            sub_id: str | None = None,
        ):
            self.create_calls.append((file_extension, file_token, file_type, sub_id))
            if sub_id is None:
                raise ExportTaskError("missing sub_id")
            return ExportTaskCreateResult(ticket="ticket-1")

    export_service = RequireSubIdExportTaskService()
    sheet_service = FakeSheetService(["sheet-xyz"])
    runner = SyncTaskRunner(
        drive_service=DriveWithMeta(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(),
        export_task_service=export_service,
        sheet_service=sheet_service,
    )

    task = SyncTaskItem(
        id="task-sheet",
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
    assert status.failed_files == 0
    assert (tmp_path / "预算表.xlsx").exists()
    assert export_service.create_calls[0][3] is None
    assert export_service.create_calls[1][3] == "sheet-xyz"
    assert sheet_service.calls == ["sheet-1"]


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


@pytest.mark.asyncio
async def test_handle_local_deleted_event_creates_tombstone(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    local_path = tmp_path / "to-delete.md"
    local_path.write_text("# data", encoding="utf-8")
    link = SyncLinkItem(
        local_path=str(local_path),
        cloud_token="doc-1",
        cloud_type="docx",
        task_id="task-del",
        updated_at=100.0,
    )
    link_service = FakeLinkService([link])
    tombstone_service = FakeTombstoneService()
    runner = SyncTaskRunner(
        link_service=link_service,
        tombstone_service=tombstone_service,
        drive_service=FakeDriveService(DriveNode(token="root", name="root", type="folder")),
    )
    task = SyncTaskItem(
        id="task-del",
        name="删除测试",
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
    local_path.unlink()
    event = FileChangeEvent(
        event_type="deleted",
        src_path=str(local_path),
        dest_path=None,
        timestamp=0.0,
    )

    await runner._handle_local_event(task, event)

    assert tombstone_service.created
    assert tombstone_service.created[0]["source"] == "local"
    assert tombstone_service.created[0]["local_path"] == str(local_path)


@pytest.mark.asyncio
async def test_run_download_enqueues_cloud_missing_delete(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    tree = DriveNode(token="root", name="根目录", type="folder", children=[])
    stale_local = tmp_path / "stale.md"
    stale_local.write_text("# stale", encoding="utf-8")
    persisted = [
        SyncLinkItem(
            local_path=str(stale_local),
            cloud_token="doc-stale",
            cloud_type="docx",
            task_id="task-cloud-del",
            updated_at=100.0,
        )
    ]
    tombstone_service = FakeTombstoneService()
    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
        link_service=FakeLinkService(persisted),
        tombstone_service=tombstone_service,
    )
    task = SyncTaskItem(
        id="task-cloud-del",
        name="云端删除测试",
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
    status = runner.get_status(task.id)
    await runner._run_download(task, status)

    assert tombstone_service.created
    assert tombstone_service.created[0]["source"] == "cloud"
    assert tombstone_service.created[0]["local_path"] == str(stale_local)


@pytest.mark.asyncio
async def test_upload_file_skips_when_hash_unchanged(tmp_path: Path) -> None:
    class UploadingFileUploader:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def upload_file(self, file_path: Path, parent_node: str, parent_type: str = "explorer"):
            self.calls.append(str(file_path))
            return type("Result", (), {"file_token": "file-token", "file_hash": "hash"})()

    file_path = tmp_path / "keep.txt"
    file_path.write_text("same-content", encoding="utf-8")
    from src.services.file_hash import calculate_file_hash as _calc

    file_hash = _calc(file_path)
    link = SyncLinkItem(
        local_path=str(file_path),
        cloud_token="file-1",
        cloud_type="file",
        task_id="task-hash",
        updated_at=10.0,
        local_hash=file_hash,
        local_size=file_path.stat().st_size,
        local_mtime=file_path.stat().st_mtime,
    )
    uploader = UploadingFileUploader()
    runner = SyncTaskRunner(link_service=FakeLinkService([link]))
    task = SyncTaskItem(
        id="task-hash",
        name="hash",
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

    await runner._upload_file(task, status, file_path, uploader)  # type: ignore[arg-type]

    assert status.skipped_files == 1
    assert uploader.calls == []


@pytest.mark.asyncio
async def test_process_pending_deletes_records_delete_failed_when_drive_delete_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    tombstone_service = FakeTombstoneService()
    await tombstone_service.create_or_refresh(
        task_id="task-del-fail",
        local_path=str(tmp_path / "gone.md"),
        cloud_token="doc-need-delete",
        cloud_type="docx",
        source="local",
        reason="test",
        expire_at=0.0,
    )
    runner = SyncTaskRunner(
        tombstone_service=tombstone_service,
        link_service=FakeLinkService([]),
    )
    task = SyncTaskItem(
        id="task-del-fail",
        name="删除失败测试",
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

    await runner._process_pending_deletes(
        task=task,
        status=status,
        drive_service=FakeDriveService(DriveNode(token="root", name="root", type="folder")),
    )

    assert any(item.status == "delete_failed" for item in status.last_files)
    assert len(tombstone_service.pending) == 1
    assert tombstone_service.pending[0]["status"] == "failed"
    assert tombstone_service.pending[0]["expire_at"] > time.time()


@pytest.mark.asyncio
async def test_process_pending_deletes_passes_cloud_type_to_drive_delete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    tombstone_service = FakeTombstoneService()
    await tombstone_service.create_or_refresh(
        task_id="task-del-ok",
        local_path=str(tmp_path / "gone.md"),
        cloud_token="doc-to-delete",
        cloud_type="docx",
        source="local",
        reason="test",
        expire_at=0.0,
    )

    class DriveWithDelete(FakeDriveService):
        def __init__(self) -> None:
            super().__init__(DriveNode(token="root", name="root", type="folder"))
            self.deleted: list[tuple[str, str | None]] = []

        async def delete_file(self, file_token: str, file_type: str | None = None) -> None:
            self.deleted.append((file_token, file_type))

    drive = DriveWithDelete()
    runner = SyncTaskRunner(
        tombstone_service=tombstone_service,
        link_service=FakeLinkService([]),
    )
    task = SyncTaskItem(
        id="task-del-ok",
        name="删除成功测试",
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

    await runner._process_pending_deletes(
        task=task,
        status=status,
        drive_service=drive,
    )

    assert drive.deleted == [("doc-to-delete", "docx")]
    assert any(item.status == "deleted" for item in status.last_files)
    assert not any(item.status == "delete_failed" for item in status.last_files)


@pytest.mark.asyncio
async def test_process_pending_deletes_removes_md_mirror_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    tombstone_service = FakeTombstoneService()
    await tombstone_service.create_or_refresh(
        task_id="task-del-md-mirror",
        local_path=str(tmp_path / "doc.md"),
        cloud_token="doc-main-token",
        cloud_type="docx",
        source="local",
        reason="test",
        expire_at=0.0,
    )

    class DriveWithMirror(FakeDriveService):
        def __init__(self) -> None:
            super().__init__(DriveNode(token="root", name="root", type="folder"))
            self.deleted: list[tuple[str, str | None]] = []

        async def delete_file(self, file_token: str, file_type: str | None = None) -> None:
            self.deleted.append((file_token, file_type))

        async def list_files(
            self,
            folder_token: str,
            page_token: str | None = None,
            page_size: int = 200,
        ) -> DriveFileList:
            if folder_token == "root-token":
                return DriveFileList(
                    files=[
                        DriveFile(
                            token="mirror-root-token",
                            name="_LarkSync_MD_Mirror",
                            type="folder",
                        )
                    ],
                    has_more=False,
                    next_page_token=None,
                )
            if folder_token == "mirror-root-token":
                return DriveFileList(
                    files=[
                        DriveFile(
                            token="mirror-md-token",
                            name="doc.md",
                            type="file",
                        )
                    ],
                    has_more=False,
                    next_page_token=None,
                )
            return DriveFileList(files=[], has_more=False, next_page_token=None)

        async def create_folder(self, parent_token: str, name: str) -> str:
            return "unused"

    drive = DriveWithMirror()
    runner = SyncTaskRunner(
        tombstone_service=tombstone_service,
        link_service=FakeLinkService([]),
    )
    task = SyncTaskItem(
        id="task-del-md-mirror",
        name="删除镜像测试",
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

    await runner._process_pending_deletes(
        task=task,
        status=status,
        drive_service=drive,
    )

    assert ("doc-main-token", "docx") in drive.deleted
    assert ("mirror-md-token", "file") in drive.deleted
    assert any(item.status == "deleted" for item in status.last_files)
    assert not any(item.status == "delete_failed" for item in status.last_files)


@pytest.mark.asyncio
async def test_process_pending_deletes_handles_cloud_already_deleted_as_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    tombstone_service = FakeTombstoneService()
    await tombstone_service.create_or_refresh(
        task_id="task-del-idem",
        local_path=str(tmp_path / "gone.md"),
        cloud_token="doc-deleted",
        cloud_type="docx",
        source="local",
        reason="test",
        expire_at=0.0,
    )

    class DriveAlreadyDeleted(FakeDriveService):
        def __init__(self) -> None:
            super().__init__(DriveNode(token="root", name="root", type="folder"))

        async def delete_file(self, file_token: str, file_type: str | None = None) -> None:
            raise RuntimeError(
                f"删除文件失败: file has been delete. token={file_token} type={file_type}"
            )

    runner = SyncTaskRunner(
        tombstone_service=tombstone_service,
        link_service=FakeLinkService([]),
    )
    task = SyncTaskItem(
        id="task-del-idem",
        name="删除幂等测试",
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

    await runner._process_pending_deletes(
        task=task,
        status=status,
        drive_service=DriveAlreadyDeleted(),
    )

    assert any(item.status == "deleted" for item in status.last_files)
    assert not any(item.status == "delete_failed" for item in status.last_files)
    assert tombstone_service.pending == []


def test_should_skip_download_for_unchanged_respects_local_hash(tmp_path: Path) -> None:
    local_path = tmp_path / "report.pdf"
    local_path.write_text("v1", encoding="utf-8")
    from src.services.file_hash import calculate_file_hash as _calc

    same_hash = _calc(local_path)
    persisted_same = SyncLinkItem(
        local_path=str(local_path),
        cloud_token="file-1",
        cloud_type="file",
        task_id="task-a",
        updated_at=100.0,
        local_hash=same_hash,
        cloud_mtime=100.0,
    )
    assert (
        SyncTaskRunner._should_skip_download_for_unchanged(
            local_path=local_path,
            cloud_mtime=100.0,
            persisted=persisted_same,
            effective_token="file-1",
            effective_type="file",
        )
        is True
    )

    persisted_diff = SyncLinkItem(
        local_path=str(local_path),
        cloud_token="file-1",
        cloud_type="file",
        task_id="task-a",
        updated_at=100.0,
        local_hash="another-hash",
        cloud_mtime=100.0,
    )
    assert (
        SyncTaskRunner._should_skip_download_for_unchanged(
            local_path=local_path,
            cloud_mtime=100.0,
            persisted=persisted_diff,
            effective_token="file-1",
            effective_type="file",
        )
        is False
    )
