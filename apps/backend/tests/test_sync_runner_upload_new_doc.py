from pathlib import Path

import pytest

from src.services.docx_service import ConvertResult
from src.services.drive_service import DriveFile, DriveFileList
from src.services.file_uploader import UploadResult
from src.services.import_task_service import ImportTaskCreateResult
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


@pytest.mark.asyncio
async def test_upload_markdown_creates_cloud_doc(tmp_path: Path) -> None:
    markdown_path = tmp_path / "测试文档.md"
    markdown_path.write_text("# Title", encoding="utf-8")

    new_doc = DriveFile(token="doc-new", name="测试文档", type="docx")
    responses = [
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[], has_more=False, next_page_token=None),
        DriveFileList(files=[new_doc], has_more=False, next_page_token=None),
    ]

    runner = SyncTaskRunner(
        docx_service=FakeDocxService(),
        file_uploader=FakeFileUploader(),
        drive_service=FakeDriveService(responses),
        link_service=FakeLinkService(),
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
