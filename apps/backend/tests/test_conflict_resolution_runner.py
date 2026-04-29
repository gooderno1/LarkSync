from pathlib import Path

import pytest

from src.services.docx_service import ConvertResult
from src.services.drive_service import DriveFile, DriveFileList, DriveNode
from src.services.file_uploader import UploadResult
from src.services.sync_link_service import SyncLinkItem
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskItem


class UploadDocxService:
    def __init__(self) -> None:
        self.replace_calls: list[tuple[str, str]] = []
        self.root_children = ["c1", "c2"]

    async def replace_document_content(
        self,
        document_id: str,
        markdown: str,
        user_id_type: str = "open_id",
        base_path=None,
        update_mode="auto",
    ) -> None:
        self.replace_calls.append((document_id, markdown))

    async def convert_markdown_with_images(
        self,
        markdown: str,
        document_id: str,
        user_id_type: str = "open_id",
        base_path=None,
    ):
        return ConvertResult(first_level_block_ids=["b1"], blocks=[{"block_id": "b1"}])

    async def get_root_block(self, document_id: str, user_id_type: str = "open_id"):
        return {"block_id": document_id, "children": list(self.root_children)}, []

    def _normalize_convert(self, convert: ConvertResult) -> ConvertResult:
        return convert


class UploadFileUploader:
    async def upload_file(
        self,
        file_path: Path,
        parent_node: str,
        parent_type: str = "explorer",
        record_db: bool = True,
    ):
        return UploadResult(file_token="file-token", file_hash="hash")


class UploadImportTaskService:
    async def create_import_task(self, **kwargs):
        raise AssertionError("冲突本地优先不应触发导入创建")


class UploadDriveService:
    def __init__(self, responses: list[DriveFileList]) -> None:
        self._responses = responses

    async def list_files(
        self, folder_token: str, page_token: str | None = None, page_size: int = 200
    ):
        if self._responses:
            return self._responses.pop(0)
        return DriveFileList(files=[], has_more=False, next_page_token=None)


class UploadLinkService:
    def __init__(self) -> None:
        self.links: dict[str, SyncLinkItem] = {}

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
        return item


class FakeBlockService:
    def __init__(self) -> None:
        self.storage: dict[tuple[str, str], list] = {}

    async def list_blocks(self, local_path: str, cloud_token: str):
        return list(self.storage.get((local_path, cloud_token), []))

    async def replace_blocks(self, local_path: str, cloud_token: str, items):
        self.storage[(local_path, cloud_token)] = list(items)


class FakeConflictService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def add_conflict(self, **kwargs):
        self.calls.append(kwargs)
        return None


class DownloadDriveService:
    def __init__(self, tree: DriveNode) -> None:
        self._tree = tree

    async def scan_folder(self, folder_token: str, name: str | None = None) -> DriveNode:
        return self._tree

    async def close(self) -> None:
        return None


class DownloadDocxService:
    async def list_blocks(self, document_id: str, user_id_type: str = "open_id"):
        return []

    async def close(self) -> None:
        return None


class DownloadTranscoder:
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


class DownloadFileDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def download(
        self, file_token: str, file_name: str, target_dir: Path, mtime: float
    ):
        self.calls.append((file_token, file_name))
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / file_name).write_bytes(b"cloud")

    async def close(self) -> None:
        return None


class DownloadFileUploader:
    async def close(self) -> None:
        return None


class DownloadImportTaskService:
    async def close(self) -> None:
        return None


class DownloadLinkService:
    def __init__(self, persisted: list[SyncLinkItem] | None = None) -> None:
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
        return None

    async def get_by_local_path(self, local_path: str):
        for item in self._persisted:
            if item.local_path == local_path:
                return item
        return None

    async def list_by_task(self, task_id: str):
        return [item for item in self._persisted if item.task_id == task_id]


@pytest.mark.asyncio
async def test_run_conflict_upload_forces_local_overwrite(tmp_path: Path) -> None:
    markdown_path = tmp_path / "冲突文档.md"
    markdown_path.write_text("# Local edit", encoding="utf-8")

    link_service = UploadLinkService()
    link_service.links[str(markdown_path)] = SyncLinkItem(
        local_path=str(markdown_path),
        cloud_token="doc-existing",
        cloud_type="docx",
        task_id="task-1",
        updated_at=1000.0,
        cloud_parent_token="fld-1",
        local_hash="baseline-hash",
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
        docx_service=UploadDocxService(),
        file_uploader=UploadFileUploader(),
        drive_service=UploadDriveService(
            [DriveFileList(files=[cloud_doc], has_more=False, next_page_token=None)]
        ),
        link_service=link_service,
        import_task_service=UploadImportTaskService(),
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

    status = await runner.run_conflict_upload(task, markdown_path)

    assert status.state == "success"
    assert status.completed_files == 1
    assert runner._docx_service.replace_calls[0][0] == "doc-existing"
    assert conflict_service.calls == []


@pytest.mark.asyncio
async def test_run_conflict_download_forces_cloud_overwrite_when_local_newer(
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "docs"
    local_root.mkdir()
    local_path = local_root / "report.pdf"
    local_path.write_bytes(b"local-newer")

    tree = DriveNode(
        token="fld-1",
        name="root",
        type="folder",
        children=[
            DriveNode(
                token="cloud-file",
                name="report.pdf",
                type="file",
                modified_time="1000",
                parent_token="fld-1",
            )
        ],
    )
    downloader = DownloadFileDownloader()
    runner = SyncTaskRunner(
        drive_service=DownloadDriveService(tree),
        docx_service=DownloadDocxService(),
        transcoder=DownloadTranscoder(),
        file_downloader=downloader,
        file_uploader=DownloadFileUploader(),
        link_service=DownloadLinkService(
            [
                SyncLinkItem(
                    local_path=str(local_path),
                    cloud_token="cloud-file",
                    cloud_type="file",
                    task_id="task-1",
                    updated_at=1000.0,
                    cloud_parent_token="fld-1",
                    local_hash="old-hash",
                    local_size=len(b"local-newer"),
                    local_mtime=2000.0,
                    cloud_mtime=1000.0,
                )
            ]
        ),
        import_task_service=DownloadImportTaskService(),
    )
    task = SyncTaskItem(
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

    status = await runner.run_conflict_download(task, local_path, "cloud-file")

    assert status.state == "success"
    assert status.completed_files == 1
    assert downloader.calls == [("cloud-file", "report.pdf")]
