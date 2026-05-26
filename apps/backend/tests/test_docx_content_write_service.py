import pytest

import src.services.docx_content_write_service as content_write_module
from src.services.docx_content_write_service import DocxContentWriteService
from src.services.docx_service import ConvertResult


def _extract_children_ids(block: dict) -> list[str]:
    return list(block.get("children") or [])


def _summarize_block_types(_blocks) -> dict[int | None, int]:
    return {}


def _make_service(
    *,
    current_blocks: list[dict],
    convert_result: ConvertResult,
    operation_log: list[tuple[str, dict]],
) -> DocxContentWriteService:
    async def _list_blocks(*args, **kwargs):
        return current_blocks

    def _find_root_block(items):
        return items[0] if items else None

    async def _convert_markdown_with_images(*args, **kwargs):
        return convert_result

    def _normalize_convert(convert):
        return convert

    async def _apply_partial_update(*args, **kwargs):
        return False

    async def _create_children_recursive(*args, **kwargs):
        operation_log.append(("create", kwargs))

    async def _delete_children(*args, **kwargs):
        operation_log.append(("delete", kwargs))

    return DocxContentWriteService(
        list_blocks=_list_blocks,
        find_root_block=_find_root_block,
        convert_markdown_with_images=_convert_markdown_with_images,
        normalize_convert=_normalize_convert,
        apply_partial_update=_apply_partial_update,
        create_children_recursive=_create_children_recursive,
        delete_children=_delete_children,
        summarize_block_types=_summarize_block_types,
        extract_children_ids=_extract_children_ids,
        service_error_cls=RuntimeError,
    )


@pytest.mark.asyncio
async def test_create_from_convert_wraps_first_level_blocks_when_root_near_limit(
    monkeypatch,
) -> None:
    monkeypatch.setattr(content_write_module, "MAX_CHILDREN_PER_BLOCK", 3)
    monkeypatch.setattr(content_write_module, "ROOT_WRAPPER_CHILD_BATCH_SIZE", 3)

    operations: list[tuple[str, dict]] = []
    convert = ConvertResult(
        first_level_block_ids=["b1", "b2"],
        blocks=[
            {"block_id": "b1", "block_type": 2, "text": {"elements": []}},
            {"block_id": "b2", "block_type": 2, "text": {"elements": []}},
        ],
    )
    service = _make_service(
        current_blocks=[{"block_id": "root", "block_type": 1, "children": []}],
        convert_result=convert,
        operation_log=operations,
    )

    ok = await service.create_from_convert(
        document_id="doc-wrap",
        root_block_id="root",
        convert=convert,
        user_id_type="open_id",
        current_root_children_count=3,
    )

    assert ok is True
    assert len(operations) == 1
    create_kwargs = operations[0][1]
    wrapper_ids = create_kwargs["child_ids"]
    assert len(wrapper_ids) == 1

    wrapper_id = wrapper_ids[0]
    block_map = create_kwargs["block_map"]
    children_map = create_kwargs["children_map"]
    assert block_map[wrapper_id]["block_type"] == 2
    assert block_map[wrapper_id]["text"]["elements"] == []
    assert children_map[wrapper_id] == ["b1", "b2"]
    assert block_map["b1"]["parent_id"] == wrapper_id
    assert block_map["b2"]["parent_id"] == wrapper_id


@pytest.mark.asyncio
async def test_replace_document_content_deletes_minimal_tail_before_create_when_root_full(
    monkeypatch,
) -> None:
    monkeypatch.setattr(content_write_module, "MAX_CHILDREN_PER_BLOCK", 6)
    monkeypatch.setattr(content_write_module, "ROOT_WRAPPER_CHILD_BATCH_SIZE", 6)

    operations: list[tuple[str, dict]] = []
    convert = ConvertResult(
        first_level_block_ids=["b1", "b2"],
        blocks=[
            {"block_id": "b1", "block_type": 2, "text": {"elements": []}},
            {"block_id": "b2", "block_type": 2, "text": {"elements": []}},
        ],
    )
    current_children = [f"c{i}" for i in range(6)]
    service = _make_service(
        current_blocks=[{"block_id": "root", "block_type": 1, "children": current_children}],
        convert_result=convert,
        operation_log=operations,
    )

    await service.replace_document_content(
        document_id="doc-overflow",
        markdown="content",
        update_mode="full",
    )

    assert [name for name, _ in operations] == ["delete", "create", "delete"]

    first_delete = operations[0][1]
    assert first_delete == {
        "document_id": "doc-overflow",
        "block_id": "root",
        "start_index": 5,
        "end_index": 6,
    }

    create_kwargs = operations[1][1]
    assert len(create_kwargs["child_ids"]) == 1

    second_delete = operations[2][1]
    assert second_delete == {
        "document_id": "doc-overflow",
        "block_id": "root",
        "start_index": 0,
        "end_index": 5,
    }
