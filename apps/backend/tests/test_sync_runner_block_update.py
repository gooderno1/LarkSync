from pathlib import Path

import pytest

from src.services.file_hash import calculate_file_hash
from src.services.sync_block_service import BlockStateItem
from src.services.sync_runner import SyncTaskRunner, SyncTaskStatus
from src.services.sync_task_service import SyncTaskItem


class FakeDocxService:
    def __init__(self, total_children: int) -> None:
        self.total_children = total_children
        self.deleted: list[tuple[int, int]] = []
        self.inserted: list[int] = []

    async def get_root_block(self, document_id: str):
        return {"block_id": "root", "children": ["x"] * self.total_children}, []

    async def delete_children(self, document_id: str, block_id: str, start_index: int, end_index: int):
        self.deleted.append((start_index, end_index))

    async def insert_markdown_block(self, *args, **kwargs) -> int:
        self.inserted.append(kwargs.get("insert_index", -1))
        return 1


class FakeBlockService:
    def __init__(self, items: list[BlockStateItem]) -> None:
        self.items = items
        self.replaced: list[BlockStateItem] | None = None
        self.replaced_calls: list[list[BlockStateItem]] = []

    async def list_blocks(self, local_path: str, cloud_token: str):
        return self.items

    async def replace_blocks(self, local_path: str, cloud_token: str, items: list[BlockStateItem]) -> None:
        self.items = items
        self.replaced = items
        self.replaced_calls.append(items)


@pytest.mark.asyncio
async def test_apply_block_update_replaces_changed_block(tmp_path: Path) -> None:
    markdown = "# Title\n\npara\n\nnew"
    file_path = tmp_path / "note.md"
    file_path.write_text(markdown, encoding="utf-8")
    file_hash = calculate_file_hash(file_path)

    task = SyncTaskItem(
        id="task-1",
        name="测试",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="partial",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    existing = [
        BlockStateItem(
            file_hash=file_hash,
            local_path=str(file_path),
            cloud_token="doc",
            block_index=0,
            block_hash="hash-a",
            block_count=1,
            updated_at=0,
            created_at=0,
        ),
        BlockStateItem(
            file_hash=file_hash,
            local_path=str(file_path),
            cloud_token="doc",
            block_index=1,
            block_hash="hash-b",
            block_count=1,
            updated_at=0,
            created_at=0,
        ),
        BlockStateItem(
            file_hash=file_hash,
            local_path=str(file_path),
            cloud_token="doc",
            block_index=2,
            block_hash="hash-c",
            block_count=1,
            updated_at=0,
            created_at=0,
        ),
    ]

    runner = SyncTaskRunner()
    runner._block_service = FakeBlockService(existing)
    docx = FakeDocxService(total_children=3)

    applied = await runner._apply_block_update(
        task=task,
        docx_service=docx,
        document_id="doc",
        markdown=markdown,
        base_path=tmp_path.as_posix(),
        file_path=file_path,
        status=SyncTaskStatus(task_id=task.id),
        force=True,
    )

    assert applied is True
    assert docx.deleted
    assert docx.inserted
    assert runner._block_service.replaced is not None


@pytest.mark.asyncio
async def test_apply_block_update_bootstraps_on_mapping_mismatch(tmp_path: Path) -> None:
    markdown = "# Title\n\npara"
    file_path = tmp_path / "note.md"
    file_path.write_text(markdown, encoding="utf-8")
    file_hash = calculate_file_hash(file_path)

    task = SyncTaskItem(
        id="task-2",
        name="测试",
        local_path=tmp_path.as_posix(),
        cloud_folder_token="root",
        cloud_folder_name=None,
        base_path=None,
        sync_mode="upload_only",
        update_mode="partial",
        enabled=True,
        created_at=0,
        updated_at=0,
    )

    existing = [
        BlockStateItem(
            file_hash=file_hash,
            local_path=str(file_path),
            cloud_token="doc",
            block_index=0,
            block_hash="hash-a",
            block_count=1,
            updated_at=0,
            created_at=0,
        ),
    ]

    runner = SyncTaskRunner()
    runner._block_service = FakeBlockService(existing)
    docx = FakeDocxService(total_children=2)

    applied = await runner._apply_block_update(
        task=task,
        docx_service=docx,
        document_id="doc",
        markdown=markdown,
        base_path=tmp_path.as_posix(),
        file_path=file_path,
        status=SyncTaskStatus(task_id=task.id),
        force=True,
    )

    assert applied is True
    assert runner._block_service.replaced_calls
    assert any(
        item.file_hash == "__bootstrap__"
        for call in runner._block_service.replaced_calls
        for item in call
    )
