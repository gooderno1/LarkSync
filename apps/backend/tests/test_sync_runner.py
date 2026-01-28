from pathlib import Path

import pytest

from src.services.drive_service import DriveNode
from src.services.file_writer import FileWriter
from src.services.sync_runner import SyncTaskRunner
from src.services.sync_task_service import SyncTaskItem


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
    async def to_markdown(self, document_id: str, blocks: list[dict]) -> str:
        return f"# {document_id}"

    async def close(self) -> None:
        return None


class FakeFileDownloader:
    async def download(self, file_token: str, file_name: str, target_dir: Path, mtime: float):
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / file_name
        path.write_bytes(b"data")

    async def close(self) -> None:
        return None


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
        ],
    )

    runner = SyncTaskRunner(
        drive_service=FakeDriveService(tree),
        docx_service=FakeDocxService(),
        transcoder=FakeTranscoder(),
        file_downloader=FakeFileDownloader(),
        file_writer=FileWriter(),
    )

    task = SyncTaskItem(
        id="task-1",
        name="测试任务",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root-token",
        base_path=None,
        sync_mode="download_only",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    await runner.run_task(task)

    status = runner.get_status(task.id)
    assert status.total_files == 3
    assert status.completed_files == 3
    assert status.failed_files == 0
    assert status.state == "success"

    assert (tmp_path / "设计文档.md").exists()
    assert (tmp_path / "spec.pdf").exists()
    assert (tmp_path / "子目录" / "note.md").exists()
