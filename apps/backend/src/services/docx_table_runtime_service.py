from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger

from src.services.transcoder import DocxParser

ConvertMarkdown = Callable[..., Awaitable[Any]]
NormalizeConvert = Callable[[Any], Any]
CreateChildrenRecursive = Callable[..., Awaitable[None]]
InsertTableRow = Callable[..., Awaitable[None]]
ListBlocks = Callable[..., Awaitable[list[dict[str, Any]]]]
TryDeleteChildren = Callable[..., Awaitable[bool]]
SplitLargeMarkdownTables = Callable[[str], str]
PatchTableProperties = Callable[[Any, str], Any]
ExtractChildrenIds = Callable[[dict[str, Any]], list[str]]
FlattenTableCells = Callable[[object], list[str]]
TableDimensions = Callable[[dict[str, Any], int], tuple[int, int]]
PlainTextBlock = Callable[[str, str], dict[str, Any]]


class DocxTableRuntimeService:
    def __init__(
        self,
        *,
        convert_markdown: ConvertMarkdown,
        normalize_convert: NormalizeConvert,
        create_children_recursive: CreateChildrenRecursive,
        insert_table_row: InsertTableRow,
        list_blocks: ListBlocks,
        try_delete_children: TryDeleteChildren,
        split_large_markdown_tables_for_convert: SplitLargeMarkdownTables,
        patch_table_properties: PatchTableProperties,
        extract_children_ids: ExtractChildrenIds,
        flatten_table_cells: FlattenTableCells,
        table_dimensions: TableDimensions,
        plain_text_block: PlainTextBlock,
    ) -> None:
        self._convert_markdown = convert_markdown
        self._normalize_convert = normalize_convert
        self._create_children_recursive = create_children_recursive
        self._insert_table_row = insert_table_row
        self._list_blocks = list_blocks
        self._try_delete_children = try_delete_children
        self._split_large_markdown_tables_for_convert = (
            split_large_markdown_tables_for_convert
        )
        self._patch_table_properties = patch_table_properties
        self._extract_children_ids = extract_children_ids
        self._flatten_table_cells = flatten_table_cells
        self._table_dimensions = table_dimensions
        self._plain_text_block = plain_text_block

    async def fallback_table_block_without_code(
        self,
        *,
        document_id: str,
        parent_block_id: str,
        table_block_id: str,
        block_map: dict[str, dict[str, Any]],
        user_id_type: str,
        insert_index: int,
        error_flag: dict[str, bool] | None = None,
    ) -> bool:
        table_block = block_map.get(table_block_id)
        if not table_block:
            return False
        parser = DocxParser(list(block_map.values()))
        table_markdown = parser.table_markdown(table_block).strip()
        if not table_markdown:
            logger.warning(
                "表格降级失败，无法生成 Markdown: document_id={} block_id={}",
                document_id,
                table_block_id,
            )
            return False
        split_markdown = self._split_large_markdown_tables_for_convert(table_markdown)
        if split_markdown != table_markdown:
            logger.warning(
                "表格块创建失败，拆分大表格重试: document_id={} parent={} block_id={}",
                document_id,
                parent_block_id,
                table_block_id,
            )
            try:
                convert = await self._convert_markdown(
                    split_markdown,
                    user_id_type=user_id_type,
                )
                convert = self._patch_table_properties(convert, split_markdown)
                convert = self._normalize_convert(convert)
                fallback_block_map = {
                    block_id: block
                    for block in convert.blocks
                    if isinstance((block_id := block.get("block_id")), str)
                }
                fallback_children_map = {
                    block_id: self._extract_children_ids(block)
                    for block_id, block in fallback_block_map.items()
                }
                await self._create_children_recursive(
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    child_ids=convert.first_level_block_ids,
                    block_map=fallback_block_map,
                    children_map=fallback_children_map,
                    user_id_type=user_id_type,
                    insert_index=insert_index,
                    image_paths=None,
                    file_paths=None,
                    error_flag=error_flag,
                )
                return True
            except Exception as exc:
                logger.warning(
                    "大表格拆分重试失败: document_id={} block_id={} error={}",
                    document_id,
                    table_block_id,
                    exc,
                )

        fallback_id = f"larksync_table_text_{uuid.uuid4().hex}"
        fallback_block = self._plain_text_block(fallback_id, table_markdown)
        logger.warning(
            "表格块创建失败，降级为普通文本重试: document_id={} parent={} block_id={}",
            document_id,
            parent_block_id,
            table_block_id,
        )
        try:
            await self._create_children_recursive(
                document_id=document_id,
                parent_block_id=parent_block_id,
                child_ids=[fallback_id],
                block_map={fallback_id: fallback_block},
                children_map={fallback_id: []},
                user_id_type=user_id_type,
                insert_index=insert_index,
                image_paths=None,
                file_paths=None,
                error_flag=error_flag,
            )
            return True
        except Exception as exc:
            logger.warning(
                "表格普通文本降级重试失败: document_id={} block_id={} error={}",
                document_id,
                table_block_id,
                exc,
            )
            return False

    async def populate_table_cells(
        self,
        *,
        document_id: str,
        table_block: dict[str, Any],
        source_table_block: dict[str, Any],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
        image_paths: dict[str, Path] | None,
        file_paths: dict[str, Path] | None,
        error_flag: dict[str, bool] | None = None,
    ) -> None:
        source_cells = self._extract_children_ids(source_table_block)
        if not source_cells:
            return
        target_cells = self._extract_children_ids(table_block)
        if not target_cells:
            table = table_block.get("table") or {}
            target_cells = self._flatten_table_cells(table.get("cells") or [])
        source_rows, source_cols = self._table_dimensions(source_table_block, len(source_cells))
        target_rows, target_cols = self._table_dimensions(table_block, len(target_cells))
        if (
            source_rows > target_rows
            and source_cols > 0
            and (target_cols <= 0 or target_cols == source_cols)
        ):
            target_cells = await self.ensure_table_row_capacity(
                document_id=document_id,
                table_block=table_block,
                current_rows=target_rows,
                desired_rows=source_rows,
                user_id_type=user_id_type,
                error_flag=error_flag,
            )
        if not target_cells:
            try:
                items = await self._list_blocks(document_id, user_id_type=user_id_type)
            except Exception as exc:
                logger.warning(
                    "获取表格单元格失败: document_id={} table_id={} error={}",
                    document_id,
                    table_block.get("block_id"),
                    exc,
                )
                if error_flag is not None:
                    error_flag["error"] = True
                return
            for item in items:
                if item.get("block_id") == table_block.get("block_id"):
                    target_cells = self._extract_children_ids(item)
                    if not target_cells:
                        table = item.get("table") or {}
                        target_cells = self._flatten_table_cells(table.get("cells") or [])
                    break
        if not target_cells:
            logger.warning(
                "表格单元格为空，跳过填充: document_id={} table_id={}",
                document_id,
                table_block.get("block_id"),
            )
            return

        if len(target_cells) != len(source_cells):
            logger.warning(
                "表格单元格数量不一致: document_id={} table_id={} source={} target={}",
                document_id,
                table_block.get("block_id"),
                len(source_cells),
                len(target_cells),
            )
        limit = min(len(source_cells), len(target_cells))
        for idx in range(limit):
            source_cell_id = source_cells[idx]
            target_cell_id = target_cells[idx]
            content_ids = children_map.get(source_cell_id, [])
            if not content_ids:
                continue
            await self._create_children_recursive(
                document_id=document_id,
                parent_block_id=target_cell_id,
                child_ids=content_ids,
                block_map=block_map,
                children_map=children_map,
                user_id_type=user_id_type,
                insert_index=0,
                image_paths=image_paths,
                file_paths=file_paths,
                error_flag=error_flag,
            )
            await self._try_delete_children(
                document_id=document_id,
                block_id=target_cell_id,
                start_index=len(content_ids),
                end_index=len(content_ids) + 1,
            )

    async def ensure_table_row_capacity(
        self,
        *,
        document_id: str,
        table_block: dict[str, Any],
        current_rows: int,
        desired_rows: int,
        user_id_type: str,
        error_flag: dict[str, bool] | None = None,
    ) -> list[str]:
        table_block_id = table_block.get("block_id")
        if not isinstance(table_block_id, str) or not table_block_id:
            return self._extract_children_ids(table_block)
        if desired_rows <= current_rows:
            return self._extract_children_ids(table_block)

        missing_rows = desired_rows - current_rows
        for _ in range(missing_rows):
            try:
                await self._insert_table_row(
                    document_id,
                    table_block_id,
                    row_index=-1,
                    user_id_type=user_id_type,
                )
            except Exception as exc:
                logger.warning(
                    "插入表格行失败: document_id={} table_id={} current_rows={} desired_rows={} error={}",
                    document_id,
                    table_block_id,
                    current_rows,
                    desired_rows,
                    exc,
                )
                if error_flag is not None:
                    error_flag["error"] = True
                return self._extract_children_ids(table_block)

        try:
            items = await self._list_blocks(document_id, user_id_type=user_id_type)
        except Exception as exc:
            logger.warning(
                "插入表格行后刷新单元格失败: document_id={} table_id={} error={}",
                document_id,
                table_block_id,
                exc,
            )
            if error_flag is not None:
                error_flag["error"] = True
            return self._extract_children_ids(table_block)

        for item in items:
            if item.get("block_id") == table_block_id:
                refreshed_cells = self._extract_children_ids(item)
                if refreshed_cells:
                    return refreshed_cells
                table = item.get("table") or {}
                return self._flatten_table_cells(table.get("cells") or [])
        return self._extract_children_ids(table_block)


__all__ = ["DocxTableRuntimeService"]
