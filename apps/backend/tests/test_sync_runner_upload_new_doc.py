from pathlib import Path

import pytest

from src.services.docx_service import ConvertResult
from src.services.drive_service import DriveFile, DriveFileList
from src.services.file_uploader import UploadResult
from src.services.file_hash import calculate_file_hash
from src.services.import_task_service import ImportTaskCreateResult
from src.services.sync_block_service import BlockStateItem
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_runner import SyncTaskRunner, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


class FakeDocxService:
    def __init__(self) -> None:
        self.replace_calls: list[tuple[str, str]] = []
        self.root_children = ["c1", "c2"]

    async def replace_document_content(
        self, document_id: str, markdown: str, user_id_type: str = "open_id", base_path=None, update_mode="auto"
    ) -> None:
        self.replace_calls.append((document_id, markdown))

    async def convert_markdown_with_images(self, markdown: str, document_id: str, user_id_type: str = "open_id", base_path=None):
        return ConvertResult(first_level_block_ids=["b1"], blocks=[{"block_id": "b1"}])

    async def get_root_block(self, document_id: str, user_id_type: str = "open_id"):
        return {"block_id": document_id, "children": list(self.root_children)}, []

    def _normalize_convert(self, convert: ConvertResult) -> ConvertResult:
        return convert


class FakeFileUploader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def upload_file(self, file_path: Path, parent_node: str, parent_type: str = "explorer", record_db: bool = True):
        self.calls.append((str(file_path), parent_node))
        return UploadResult(file_token="file-token", file_hash="hash")


class FakeImportTaskService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_import_task(self, **kwargs):
        self.calls.append(kwargs)
        return ImportTaskCreateResult(ticket="ticket-1")


class FakeFailedImportTaskService(FakeImportTaskService):
    async def create_import_task(self, **kwargs):
        self.calls.append(kwargs)
        raise RuntimeError("import failed")


class FakeDriveService:
    def __init__(self, responses: list[DriveFileList]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str | None]] = []
        self.deleted: list[tuple[str, str | None]] = []

    async def list_files(self, folder_token: str, page_token: str | None = None, page_size: int = 200):
        self.calls.append((folder_token, page_token))
        if self._responses:
            return self._responses.pop(0)
        return DriveFileList(files=[], has_more=False, next_page_token=None)

    async def delete_file(self, file_token: str, file_type: str | None = None):
        self.deleted.append((file_token, file_type))


class FakeMirrorDriveService(FakeDriveService):
    def __init__(self) -> None:
        super().__init__(responses=[])
        self.created_folders: list[tuple[str, str]] = []
        self._folder_counter = 0

    async def create_folder(self, parent_token: str, name: str) -> str:
        self.created_folders.append((parent_token, name))
        self._folder_counter += 1
        return f"folder-{self._folder_counter}"


class FakeLinkService:
    def __init__(self) -> None:
        self.links: dict[str, SyncLinkItem] = {}
        self.calls: list[SyncLinkItem] = []

    async def get_by_local_path(self, local_path: str):
        return self.links.get(local_path)

    async def upsert_link(
        self,
        local_path: str,
        cloud_token: str,
        cloud_type: str,
        task_id: str,
        updated_at=None,
        cloud_parent_token: str | None = None,
        local_hash: str | None = None,
        local_size: int | None = None,
        local_mtime: float | None = None,
        cloud_revision: str | None = None,
        cloud_mtime: float | None = None,
        local_resource_signature: str | None = None,
        resource_sync_revision: str | None = None,
    ):
        item = SyncLinkItem(
            local_path=local_path,
            cloud_token=cloud_token,
            cloud_type=cloud_type,
            task_id=task_id,
            updated_at=0.0 if updated_at is None else float(updated_at),
            cloud_parent_token=cloud_parent_token,
            local_hash=local_hash,
            local_size=local_size,
            local_mtime=local_mtime,
            cloud_revision=cloud_revision,
            cloud_mtime=cloud_mtime,
            local_resource_signature=local_resource_signature,
            resource_sync_revision=resource_sync_revision,
        )
        self.links[local_path] = item
        self.calls.append(item)
        return item

    async def list_by_task(self, task_id: str):
        return [item for item in self.links.values() if item.task_id == task_id]

    async def delete_by_local_path(self, local_path: str):
        return self.links.pop(local_path, None) is not None


class FakeBlockService:
    def __init__(self) -> None:
        self.replace_calls = 0
        self.storage: dict[tuple[str, str], list] = {}

    async def list_blocks(self, local_path: str, cloud_token: str):
        return list(self.storage.get((local_path, cloud_token), []))

    async def replace_blocks(self, local_path: str, cloud_token: str, items):
        self.replace_calls += 1
        self.storage[(local_path, cloud_token)] = list(items)


class FakeConflictService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def add_conflict(self, **kwargs):
        self.calls.append(kwargs)
        return None


@pytest.mark.asyncio
async def test_upload_markdown_creates_cloud_doc(tmp_path: Path) -> None:
    markdown_path = tmp_path / "测试文档.md"
    markdown_path.write_text("# Title", encoding="utf-8")
    file_hash = calculate_file_hash(markdown_path)

    new_doc = DriveFile(
        token="doc-new",
        name="测试文档",
        type="docx",
        modified_time="1001",
    )
    responses = [
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[new_doc], has_more=False, next_page_token=None),
    ]
    link_service = FakeLinkService()

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()
    runner._import_poll_attempts = 3
    runner._import_poll_interval = 0.0

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert runner._docx_service.replace_calls == []
    assert runner._block_service.replace_calls == 1
    assert runner._file_uploader.calls[0][1] == "fld-1"
    assert runner._import_task_service.calls[0]["file_extension"] == "md"
    assert runner._drive_service.deleted == [("file-token", "file")]
    assert link_service.calls[0].updated_at == 1001.0
    assert link_service.calls[0].cloud_mtime == 1001.0
    assert link_service.calls[0].local_hash == file_hash
    assert link_service.calls[0].cloud_revision == "doc-new@1001000"


@pytest.mark.asyncio
async def test_upload_new_markdown_with_local_image_runs_block_replace_after_import(
    tmp_path: Path,
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "logo.png").write_bytes(b"img")
    markdown_path = tmp_path / "图片文档.md"
    markdown_path.write_text("# Title\n\n![](assets/logo.png)", encoding="utf-8")

    new_doc = DriveFile(token="doc-new", name="图片文档", type="docx")
    responses = [
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[new_doc], has_more=False, next_page_token=None),
    ]
    link_service = FakeLinkService()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()
    runner._import_poll_attempts = 3
    runner._import_poll_interval = 0.0
    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert runner._docx_service.replace_calls[0][0] == "doc-new"
    assert "#local-images-v2" in (
        link_service.links[str(markdown_path)].cloud_revision or ""
    )


@pytest.mark.asyncio
async def test_upload_markdown_with_local_image_repairs_same_hash_link_once(
    tmp_path: Path,
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "logo.png").write_bytes(b"img")
    markdown_path = tmp_path / "图片修复.md"
    markdown_path.write_text("# Title\n\n![](assets/logo.png)", encoding="utf-8")
    file_hash = calculate_file_hash(markdown_path)

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
        local_hash=file_hash,
        cloud_revision="doc-existing@1",
    )
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()
    runner._block_service.storage[(str(markdown_path), "doc-existing")] = [
        BlockStateItem(
            file_hash=file_hash,
            local_path=str(markdown_path),
            cloud_token="doc-existing",
            block_index=0,
            block_hash="old",
            block_count=1,
            updated_at=0.0,
            created_at=0.0,
        )
    ]
    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.skipped_files == 0
    assert status.completed_files == 1
    assert runner._docx_service.replace_calls[0][0] == "doc-existing"
    assert "#local-images-v2" in (
        link_service.links[str(markdown_path)].cloud_revision or ""
    )


@pytest.mark.asyncio
async def test_upload_markdown_skips_when_resource_baseline_matches_current_cloud_revision(
    tmp_path: Path,
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "logo.png").write_bytes(b"img")
    attachment_dir = tmp_path / "attachments"
    attachment_dir.mkdir()
    (attachment_dir / "brief.pdf").write_bytes(b"pdf")
    markdown_path = tmp_path / "资源基线.md"
    markdown_path.write_text(
        "# Title\n\n![](assets/logo.png)\n\n[brief](attachments/brief.pdf)\n",
        encoding="utf-8",
    )
    file_hash = calculate_file_hash(markdown_path)

    link_service = FakeLinkService()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    resource_signature = runner._calculate_local_resource_signature(
        markdown_path.read_text(encoding="utf-8"),
        markdown_path.parent,
    )
    assert resource_signature is not None

    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=1000.0,
        local_hash=file_hash,
        local_size=markdown_path.stat().st_size,
        local_mtime=markdown_path.stat().st_mtime,
        cloud_revision="doc-existing@1000000",
        cloud_mtime=1000.0,
        local_resource_signature=resource_signature,
        resource_sync_revision="doc-existing@1000000",
    )
    runner._block_service = FakeBlockService()
    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.skipped_files == 1
    assert status.completed_files == 0
    assert runner._docx_service.replace_calls == []


@pytest.mark.asyncio
async def test_upload_file_updates_link_timestamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1700000000.0
    monkeypatch.setattr("src.services.sync_runner.time.time", lambda: now)
    file_path = tmp_path / "demo.txt"
    file_path.write_text("data", encoding="utf-8")

    link_service = FakeLinkService()
    runner = SyncTaskRunner(
        file_uploader=FakeFileUploader(),
        link_service=link_service,
    )
    task = SyncTaskItem(
        id="task-upload",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_file(task, status, file_path, runner._file_uploader)  # type: ignore[arg-type]

    assert link_service.calls[-1].updated_at == now


@pytest.mark.asyncio
async def test_upload_file_replaces_previous_cloud_file_and_cleans_same_name_duplicates(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"new-pdf")

    old_token = "file-old"
    duplicate_token = "file-duplicate"
    responses = [
        DriveFileList(
            files=[
                DriveFile(token=old_token, name="report.pdf", type="file"),
                DriveFile(token=duplicate_token, name="report.pdf", type="file"),
                DriveFile(token="file-other", name="other.pdf", type="file"),
            ],
            has_more=False,
            next_page_token=None,
        )
    ]
    drive_service = FakeDriveService(responses)
    link_service = FakeLinkService()
    await link_service.upsert_link(
        local_path=str(file_path),
        cloud_token=old_token,
        cloud_type="file",
        task_id="task-upload",
        updated_at=1.0,
        cloud_parent_token="fld-1",
        local_hash="old-hash",
        local_size=1,
        local_mtime=1.0,
    )
    runner = SyncTaskRunner(
        file_uploader=FakeFileUploader(),
        link_service=link_service,
        drive_service=drive_service,
    )
    task = SyncTaskItem(
        id="task-upload",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_file(
        task,
        status,
        file_path,
        runner._file_uploader,  # type: ignore[arg-type]
        drive_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert drive_service.deleted == [(old_token, "file"), (duplicate_token, "file")]
    assert link_service.links[str(file_path)].cloud_token == "file-token"


@pytest.mark.asyncio
async def test_upload_markdown_reuses_existing_doc_without_new_import(tmp_path: Path) -> None:
    markdown_path = tmp_path / "复用文档.md"
    markdown_path.write_text("# Reuse", encoding="utf-8")

    existing_doc = DriveFile(token="doc-existing", name="复用文档", type="docx")
    responses = [DriveFileList(files=[existing_doc], has_more=False, next_page_token=None)]

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=FakeLinkService(),
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="full",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert runner._import_task_service.calls == []
    assert runner._file_uploader.calls == []
    assert runner._docx_service.replace_calls[0][0] == "doc-existing"
    assert runner._drive_service.deleted == []


@pytest.mark.asyncio
async def test_upload_markdown_blocks_bidirectional_overwrite_when_cloud_changed(
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "冲突文档.md"
    markdown_path.write_text("# Baseline", encoding="utf-8")
    baseline_hash = calculate_file_hash(markdown_path)
    markdown_path.write_text("# Local edit", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=1000.0,
        cloud_parent_token="fld-1",
        local_hash=baseline_hash,
        cloud_mtime=1000.0,
    )
    cloud_doc = DriveFile(
        token="doc-existing",
        name="冲突文档",
        type="docx",
        modified_time="1005",
    )
    conflict_service = FakeConflictService()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(
            [DriveFileList(files=[cloud_doc], has_more=False, next_page_token=None)]
        ),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
        conflict_service=conflict_service,
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="full",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.completed_files == 0
    assert status.skipped_files == 1
    assert runner._docx_service.replace_calls == []
    assert len(conflict_service.calls) == 1
    assert conflict_service.calls[0]["cloud_token"] == "doc-existing"
    assert any(event.status == "conflict" for event in status.last_files)


@pytest.mark.asyncio
async def test_upload_markdown_new_doc_initializes_baseline_before_bidirectional_guard(
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "首次创建文档.md"
    markdown_path.write_text("# Local only", encoding="utf-8")

    new_doc = DriveFile(
        token="doc-new",
        name="首次创建文档",
        type="docx",
        modified_time="1005",
    )
    responses = [
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[new_doc], has_more=False, next_page_token=None),
        DriveFileList(files=[new_doc], has_more=False, next_page_token=None),
    ]
    link_service = FakeLinkService()
    conflict_service = FakeConflictService()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
        conflict_service=conflict_service,
    )
    runner._block_service = FakeBlockService()
    runner._import_poll_attempts = 3
    runner._import_poll_interval = 0.0

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert status.skipped_files == 0
    assert conflict_service.calls == []
    assert all(event.status != "conflict" for event in status.last_files)
    assert link_service.calls[0].cloud_mtime == 1005.0
    assert link_service.calls[0].updated_at == 1005.0


@pytest.mark.asyncio
async def test_upload_markdown_reimports_existing_doc_when_table_exceeds_block_limit(
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "大表格文档.md"
    markdown_path.write_text(
        "\n".join(
            [
                "| H1 | H2 |",
                "| --- | --- |",
                *[f"| r{i}c1 | r{i}c2 |" for i in range(1, 10)],
            ]
        ),
        encoding="utf-8",
    )

    old_doc = DriveFile(token="doc-old", name="大表格文档", type="docx")
    new_doc = DriveFile(token="doc-new", name="大表格文档", type="docx")
    responses = [
        DriveFileList(files=[old_doc], has_more=False, next_page_token=None),
        DriveFileList(files=[old_doc, new_doc], has_more=False, next_page_token=None),
        DriveFileList(files=[old_doc, new_doc], has_more=False, next_page_token=None),
    ]

    link_service = FakeLinkService()
    await link_service.upsert_link(
        local_path=str(markdown_path),
        cloud_token="doc-old",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
        cloud_parent_token="fld-1",
    )

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()
    runner._import_poll_attempts = 2
    runner._import_poll_interval = 0.0

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert runner._docx_service.replace_calls == []
    assert runner._import_task_service.calls[0]["file_name"] == "大表格文档"
    assert runner._drive_service.deleted == [("file-token", "file"), ("doc-old", "docx")]
    assert link_service.links[str(markdown_path)].cloud_token == "doc-new"
    assert runner._block_service.storage[(str(markdown_path), "doc-old")] == []
    assert runner._block_service.storage[(str(markdown_path), "doc-new")]


@pytest.mark.asyncio
async def test_upload_markdown_syncs_md_copy_to_cloud_mirror_folder(tmp_path: Path) -> None:
    markdown_path = tmp_path / "镜像文档.md"
    markdown_path.write_text("# Mirror", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
    )

    mirror_drive = FakeMirrorDriveService()
    uploader = FakeFileUploader()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=uploader,
        drive_service=mirror_drive,
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="full",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        uploader,
        mirror_drive,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert any(name == "_LarkSync_MD_Mirror" for _, name in mirror_drive.created_folders)
    assert len(uploader.calls) == 1
    assert uploader.calls[0][0] == str(markdown_path)
    assert any(event.status == "mirrored" for event in status.last_files)


@pytest.mark.asyncio
async def test_upload_markdown_doc_only_mode_skips_cloud_mirror(tmp_path: Path) -> None:
    markdown_path = tmp_path / "仅文档上传.md"
    markdown_path.write_text("# Doc only", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
    )

    mirror_drive = FakeMirrorDriveService()
    uploader = FakeFileUploader()
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=uploader,
        drive_service=mirror_drive,
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="full",
        md_sync_mode="doc_only",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        uploader,
        mirror_drive,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert not any(name == "_LarkSync_MD_Mirror" for _, name in mirror_drive.created_folders)
    assert not any(event.status == "mirrored" for event in status.last_files)


@pytest.mark.asyncio
async def test_upload_path_skips_md_when_mode_is_download_only(tmp_path: Path) -> None:
    markdown_path = tmp_path / "只下载模式.md"
    markdown_path.write_text("# Local", encoding="utf-8")

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=FakeLinkService(),
        import_task_service=FakeImportTaskService(),
    )
    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="auto",
        md_sync_mode="download_only",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_path(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.completed_files == 0
    assert status.failed_files == 0
    assert status.skipped_files == 1
    assert any(
        event.status == "skipped" and "仅下载" in (event.message or "")
        for event in status.last_files
    )


@pytest.mark.asyncio
async def test_upload_markdown_with_file_link_uses_file_upload(tmp_path: Path) -> None:
    markdown_path = tmp_path / "文件模式.md"
    markdown_path.write_text("# Title", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="file-legacy-token",
        cloud_type="file",
        task_id="task-1",
        updated_at=0.0,
    )

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="partial",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert runner._docx_service.replace_calls == []
    assert runner._block_service.replace_calls == 0
    assert runner._file_uploader.calls[0][1] == "fld-1"
    assert link_service.links[str(markdown_path)].cloud_type == "file"
    assert link_service.links[str(markdown_path)].cloud_token == "file-token"


@pytest.mark.asyncio
async def test_upload_markdown_import_failure_still_cleans_source_md(tmp_path: Path) -> None:
    markdown_path = tmp_path / "导入失败清理.md"
    markdown_path.write_text("# Title", encoding="utf-8")

    drive = FakeDriveService(
        [DriveFileList(files=[], has_more=False, next_page_token=None)]
    )
    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=drive,
        link_service=FakeLinkService(),
        import_task_service=FakeFailedImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="auto",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        drive,
        runner._import_task_service,
    )

    assert status.failed_files == 1
    assert status.completed_files == 0
    assert drive.deleted == [("file-token", "file")]


@pytest.mark.asyncio
async def test_upload_markdown_partial_mode_raises_without_block_state(tmp_path: Path) -> None:
    markdown_path = tmp_path / "局部回退测试.md"
    markdown_path.write_text("# Title", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
    )

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    async def _raise_partial(*args, **kwargs):
        raise RuntimeError("缺少块级状态，无法局部更新")

    runner._apply_block_update = _raise_partial  # type: ignore[method-assign]

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="partial",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    with pytest.raises(RuntimeError, match="缺少块级状态，无法局部更新"):
        await runner._upload_markdown(
            task,
            status,
            markdown_path,
            runner._docx_service,
            runner._file_uploader,
            runner._drive_service,
            runner._import_task_service,
        )


@pytest.mark.asyncio
async def test_upload_markdown_partial_bootstraps_block_state(tmp_path: Path) -> None:
    markdown_path = tmp_path / "初始化块状态.md"
    markdown_path.write_text("# Title", encoding="utf-8")

    link_service = FakeLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=0.0,
    )

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService([]),
        link_service=link_service,
        import_task_service=FakeImportTaskService(),
    )
    runner._block_service = FakeBlockService()

    async def _apply_success(*args, **kwargs):
        return True

    runner._apply_block_update = _apply_success  # type: ignore[method-assign]

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="fld-1",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="bidirectional",
        update_mode="partial",
        enabled=True,
        created_at=0,
        updated_at=0,
    )
    status = SyncTaskStatus(task_id=task.id)

    await runner._upload_markdown(
        task,
        status,
        markdown_path,
        runner._docx_service,
        runner._file_uploader,
        runner._drive_service,
        runner._import_task_service,
    )

    assert status.failed_files == 0
    assert status.completed_files == 1
    assert runner._block_service.replace_calls == 1
    assert any(event.status == "bootstrapped" for event in status.last_files)
