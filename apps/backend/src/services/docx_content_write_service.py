from __future__ import annotations

import uuid
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

MAX_CHILDREN_PER_BLOCK = 20000
ROOT_WRAPPER_CHILD_BATCH_SIZE = MAX_CHILDREN_PER_BLOCK
ROOT_WRAPPER_TEXT = "\u200b"


def _build_wrapper_text_elements() -> list[dict[str, Any]]:
    return [
        {
            "text_run": {
                "content": ROOT_WRAPPER_TEXT,
                "text_element_style": {
                    "bold": False,
                    "inline_code": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                },
            }
        }
    ]


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
        children = list(root_block.get("children") or [])
        logger.info(
            "根块信息: block_id={} children={}",
            root_block.get("block_id"),
            len(children),
        )

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
            remaining_old_children = len(children)
            overflow = (
                remaining_old_children
                + len(convert.first_level_block_ids)
                - MAX_CHILDREN_PER_BLOCK
            )
            if overflow > 0:
                delete_start = max(0, remaining_old_children - overflow)
                logger.warning(
                    "根块子节点接近上限，先删除尾部旧块腾位: document_id={} current_children={} new_first_level={} overflow={}",
                    document_id,
                    remaining_old_children,
                    len(convert.first_level_block_ids),
                    overflow,
                )
                await self._delete_children(
                    document_id=document_id,
                    block_id=root_block["block_id"],
                    start_index=delete_start,
                    end_index=remaining_old_children,
                )
                remaining_old_children = delete_start

            ok = await self.create_from_convert(
                document_id=document_id,
                root_block_id=root_block["block_id"],
                convert=convert,
                user_id_type=user_id_type,
                current_root_children_count=remaining_old_children,
            )
            if not ok:
                raise self._service_error_cls("创建块失败，已中止替换")
            logger.info(
                "新内容已创建: document_id={} blocks={}",
                document_id,
                len(convert.blocks),
            )

            if remaining_old_children > 0:
                await self._delete_children(
                    document_id=document_id,
                    block_id=root_block["block_id"],
                    start_index=0,
                    end_index=remaining_old_children,
                )
                logger.info(
                    "旧内容已删除: document_id={} count={}",
                    document_id,
                    remaining_old_children,
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
        current_root_children_count: int | None = None,
    ) -> bool:
        if current_root_children_count is None:
            current_root_children_count = await self._resolve_root_children_count(
                document_id=document_id,
                root_block_id=root_block_id,
                user_id_type=user_id_type,
            )
        convert = self._prepare_convert_for_root_limit(
            convert,
            current_root_children_count=current_root_children_count,
        )
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
        if error_flag["error"]:
            await self._rollback_failed_root_insert(
                document_id=document_id,
                root_block_id=root_block_id,
                user_id_type=user_id_type,
                current_root_children_count=current_root_children_count,
                insert_index=insert_index,
            )
            return False
        return True

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

    def _prepare_convert_for_root_limit(
        self,
        convert: Any,
        *,
        current_root_children_count: int,
    ) -> Any:
        first_level_ids = list(convert.first_level_block_ids)
        if not first_level_ids:
            return convert

        if (
            len(first_level_ids) <= MAX_CHILDREN_PER_BLOCK
            and current_root_children_count + len(first_level_ids) <= MAX_CHILDREN_PER_BLOCK
        ):
            return convert
        if len(first_level_ids) <= 1:
            return convert

        wrapper_size = max(1, min(ROOT_WRAPPER_CHILD_BATCH_SIZE, MAX_CHILDREN_PER_BLOCK))
        block_map = {
            block_id: block
            for block in convert.blocks
            if isinstance((block_id := block.get("block_id")), str)
        }
        wrapper_ids: list[str] = []
        wrapper_blocks: list[dict[str, Any]] = []
        for index in range(0, len(first_level_ids), wrapper_size):
            chunk = first_level_ids[index : index + wrapper_size]
            wrapper_id = f"larksync-root-wrapper-{index // wrapper_size}-{uuid.uuid4().hex}"
            wrapper_ids.append(wrapper_id)
            wrapper_blocks.append(
                {
                    "block_id": wrapper_id,
                    "block_type": 2,
                    "children": list(chunk),
                    # Feishu rejects empty text elements for wrapper paragraphs.
                    "text": {"elements": _build_wrapper_text_elements()},
                }
            )
            for child_id in chunk:
                child_block = block_map.get(child_id)
                if child_block is not None:
                    child_block["parent_id"] = wrapper_id

        logger.warning(
            "一级块数量需要压缩为透明容器: current_children={} original_first_level={} wrapped_first_level={}",
            current_root_children_count,
            len(first_level_ids),
            len(wrapper_ids),
        )
        convert.first_level_block_ids = wrapper_ids
        convert.blocks = [*convert.blocks, *wrapper_blocks]
        return convert

    async def _resolve_root_children_count(
        self,
        *,
        document_id: str,
        root_block_id: str,
        user_id_type: str,
    ) -> int:
        items = await self._list_blocks(document_id, user_id_type=user_id_type)
        for item in items:
            if item.get("block_id") == root_block_id:
                return len(list(item.get("children") or []))
        return 0

    async def _rollback_failed_root_insert(
        self,
        *,
        document_id: str,
        root_block_id: str,
        user_id_type: str,
        current_root_children_count: int,
        insert_index: int,
    ) -> None:
        try:
            items = await self._list_blocks(document_id, user_id_type=user_id_type)
            current_root = None
            for item in items:
                if item.get("block_id") == root_block_id:
                    current_root = item
                    break
            if current_root is None:
                return
            current_children = list(current_root.get("children") or [])
            inserted_count = len(current_children) - current_root_children_count
            if inserted_count <= 0:
                return
            start_index = (
                current_root_children_count
                if insert_index < 0
                else min(insert_index, len(current_children))
            )
            end_index = min(start_index + inserted_count, len(current_children))
            if end_index <= start_index:
                return
            logger.warning(
                "创建块失败，回滚已插入的顶层块: document_id={} start_index={} end_index={} inserted_count={}",
                document_id,
                start_index,
                end_index,
                inserted_count,
            )
            await self._delete_children(
                document_id=document_id,
                block_id=root_block_id,
                start_index=start_index,
                end_index=end_index,
            )
        except Exception as exc:
            logger.error(
                "创建块失败后的顶层回滚也失败: document_id={} root_block_id={} error={}",
                document_id,
                root_block_id,
                exc,
            )


__all__ = ["DocxContentWriteService"]
