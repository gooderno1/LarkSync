from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from loguru import logger

ListBlocksFn = Callable[..., Awaitable[list[dict[str, Any]]]]
FindRootBlockFn = Callable[[Iterable[dict[str, Any]]], dict[str, Any] | None]
ConvertMarkdownWithImagesFn = Callable[..., Awaitable[Any]]
NormalizeConvertFn = Callable[[Any], Any]
ApplyPartialUpdateFn = Callable[..., Awaitable[bool]]
CreateChildrenRecursiveFn = Callable[..., Awaitable[None]]
DeleteChildrenFn = Callable[..., Awaitable[None]]
SummarizeBlockTypesFn = Callable[[Iterable[dict[str, Any]]], dict[int | None, int]]
ExtractChildrenIdsFn = Callable[[dict[str, Any]], list[str]]


class DocxContentWriteService:
    def __init__(
        self,
        *,
        list_blocks: ListBlocksFn,
        find_root_block: FindRootBlockFn,
        convert_markdown_with_images: ConvertMarkdownWithImagesFn,
        normalize_convert: NormalizeConvertFn,
        apply_partial_update: ApplyPartialUpdateFn,
        create_children_recursive: CreateChildrenRecursiveFn,
        delete_children: DeleteChildrenFn,
        summarize_block_types: SummarizeBlockTypesFn,
        extract_children_ids: ExtractChildrenIdsFn,
        service_error_cls: type[Exception],
    ) -> None:
        self._list_blocks = list_blocks
        self._find_root_block = find_root_block
        self._convert_markdown_with_images = convert_markdown_with_images
        self._normalize_convert = normalize_convert
        self._apply_partial_update = apply_partial_update
        self._create_children_recursive = create_children_recursive
        self._delete_children = delete_children
        self._summarize_block_types = summarize_block_types
        self._extract_children_ids = extract_children_ids
        self._service_error_cls = service_error_cls

    async def replace_document_content(
        self,
        *,
        document_id: str,
        markdown: str,
        user_id_type: str = "open_id",
        base_path: str | Path | None = None,
        update_mode: str = "auto",
    ) -> None:
        logger.info(
            "替换文档内容: document_id={} length={}", document_id, len(markdown)
        )
        items = await self._list_blocks(document_id, user_id_type=user_id_type)
        root_block = self._find_root_block(items)
        if not root_block:
            raise self._service_error_cls("未找到文档根 Block")

        convert = await self._convert_markdown_with_images(
            markdown,
            document_id=document_id,
            user_id_type=user_id_type,
            base_path=base_path,
        )
        convert = self._normalize_convert(convert)
        logger.info(
            "转换结果: document_id={} blocks={} first_level={} types={}",
            document_id,
            len(convert.blocks),
            len(convert.first_level_block_ids),
            self._summarize_block_types(convert.blocks),
        )

        children = root_block.get("children") or []
        logger.info(
            "根块信息: block_id={} children={}",
            root_block.get("block_id"),
            len(children),
        )
        if update_mode not in {"auto", "partial", "full"}:
            update_mode = "auto"

        partial_applied = False
        if update_mode in {"auto", "partial"} and children:
            partial_applied = await self._apply_partial_update(
                document_id=document_id,
                root_block_id=root_block["block_id"],
                current_children=children,
                current_blocks=items,
                convert=convert,
                user_id_type=user_id_type,
                force=update_mode == "partial",
            )

        if not partial_applied:
            ok = await self.create_from_convert(
                document_id=document_id,
                root_block_id=root_block["block_id"],
                convert=convert,
                user_id_type=user_id_type,
            )
            if not ok:
                raise self._service_error_cls("创建块失败，已中止替换")
            logger.info(
                "新内容已创建: document_id={} blocks={}",
                document_id,
                len(convert.blocks),
            )

            if children:
                await self._delete_children(
                    document_id=document_id,
                    block_id=root_block["block_id"],
                    start_index=0,
                    end_index=len(children),
                )
                logger.info(
                    "旧内容已删除: document_id={} count={}", document_id, len(children)
                )
        logger.info(
            "替换完成: document_id={} blocks={}",
            document_id,
            len(convert.blocks),
        )

    async def create_from_convert(
        self,
        *,
        document_id: str,
        root_block_id: str,
        convert: Any,
        user_id_type: str,
        insert_index: int = -1,
    ) -> bool:
        error_flag = {"error": False}
        block_map = {block.get("block_id"): block for block in convert.blocks}
        children_map = {
            block.get("block_id"): self._extract_children_ids(block)
            for block in convert.blocks
        }
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=root_block_id,
            child_ids=convert.first_level_block_ids,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index,
            image_paths=convert.image_paths,
            file_paths=convert.file_paths,
            error_flag=error_flag,
        )
        return not error_flag["error"]

    async def insert_markdown_block(
        self,
        *,
        document_id: str,
        root_block_id: str,
        markdown: str,
        base_path: str | Path | None,
        user_id_type: str = "open_id",
        insert_index: int = -1,
    ) -> int:
        convert = await self._convert_markdown_with_images(
            markdown,
            document_id=document_id,
            user_id_type=user_id_type,
            base_path=base_path,
        )
        convert = self._normalize_convert(convert)
        ok = await self.create_from_convert(
            document_id=document_id,
            root_block_id=root_block_id,
            convert=convert,
            user_id_type=user_id_type,
            insert_index=insert_index,
        )
        if not ok:
            raise self._service_error_cls("创建块失败，已中止插入")
        return len(convert.first_level_block_ids)


__all__ = ["DocxContentWriteService"]
