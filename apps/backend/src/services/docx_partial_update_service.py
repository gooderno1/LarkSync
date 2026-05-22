from __future__ import annotations

import difflib
import hashlib
from collections import Counter
from typing import Any, Awaitable, Callable

from loguru import logger

from src.services.transcoder import (
    BLOCK_TYPE_FILE,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_TABLE,
    DocxParser,
)

DeleteChildren = Callable[..., Awaitable[None]]
CreateChildrenRecursive = Callable[..., Awaitable[None]]
ExtractChildrenIds = Callable[[dict[str, Any]], list[str]]


class DocxPartialUpdateService:
    def __init__(
        self,
        *,
        delete_children: DeleteChildren,
        create_children_recursive: CreateChildrenRecursive,
        extract_children_ids: ExtractChildrenIds,
    ) -> None:
        self._delete_children = delete_children
        self._create_children_recursive = create_children_recursive
        self._extract_children_ids = extract_children_ids

    async def apply_partial_update(
        self,
        *,
        document_id: str,
        root_block_id: str,
        current_children: list[str],
        current_blocks: list[dict[str, Any]],
        convert: Any,
        user_id_type: str,
        force: bool,
    ) -> bool:
        current_map = {block.get("block_id"): block for block in current_blocks}
        current_ids = [block_id for block_id in current_children if block_id in current_map]
        if not current_ids:
            return False

        desired_ids = convert.first_level_block_ids
        if not desired_ids:
            return False
        if not force and any(block.get("block_type") == BLOCK_TYPE_TABLE for block in convert.blocks):
            logger.info("局部更新跳过: 检测到表格块，退回全量覆盖")
            return False

        current_parser = DocxParser(current_blocks)
        desired_parser = DocxParser(convert.blocks)

        current_sigs = [
            _block_signature(block_id, current_map, current_parser)
            for block_id in current_ids
        ]
        desired_map = {block.get("block_id"): block for block in convert.blocks}
        desired_sigs = [
            _block_signature(block_id, desired_map, desired_parser)
            for block_id in desired_ids
        ]
        if not force and (_has_duplicate_signatures(current_sigs) or _has_duplicate_signatures(desired_sigs)):
            logger.info("局部更新跳过: 检测到重复块签名，退回全量覆盖")
            return False
        if not force:
            anchors = _unique_anchor_pairs(current_sigs, desired_sigs)
            min_len = min(len(current_sigs), len(desired_sigs))
            anchor_ratio = len(anchors) / max(min_len, 1)
            if min_len >= 8 and len(anchors) < 2:
                logger.info("局部更新跳过: 唯一锚点不足 (anchors={})", len(anchors))
                return False
            if min_len >= 20 and anchor_ratio < 0.2:
                logger.info(
                    "局部更新跳过: 唯一锚点占比过低 (anchors={} ratio={:.2f})",
                    len(anchors),
                    anchor_ratio,
                )
                return False
            if anchors:
                desired_order = [item[1] for item in anchors]
                if desired_order != sorted(desired_order):
                    logger.info("局部更新跳过: 锚点顺序不一致，退回全量覆盖")
                    return False

        matcher = difflib.SequenceMatcher(a=current_sigs, b=desired_sigs)
        opcodes = matcher.get_opcodes()
        changed = sum((i2 - i1) for tag, i1, i2, _, _ in opcodes if tag != "equal")
        change_ratio = changed / max(len(current_sigs), 1)
        logger.info(
            "局部更新评估: document_id={} current={} desired={} ops={} change_ratio={:.2f}",
            document_id,
            len(current_sigs),
            len(desired_sigs),
            len(opcodes),
            change_ratio,
        )

        if not force and (change_ratio > 0.6 or len(opcodes) > 50):
            logger.info("局部更新跳过: change_ratio 太高或 ops 过多，退回全量覆盖")
            return False
        if not force and matcher.ratio() < 0.55:
            logger.info("局部更新跳过: 相似度过低 (ratio={:.2f})", matcher.ratio())
            return False

        block_map = {block.get("block_id"): block for block in convert.blocks}
        children_map = {
            block.get("block_id"): self._extract_children_ids(block)
            for block in convert.blocks
        }

        offset = 0
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            start = i1 + offset
            end = i2 + offset
            if tag in {"delete", "replace"} and end > start:
                await self._delete_children(
                    document_id=document_id,
                    block_id=root_block_id,
                    start_index=start,
                    end_index=end,
                )
                offset -= (i2 - i1)
            if tag in {"insert", "replace"} and j2 > j1:
                await self._create_children_recursive(
                    document_id=document_id,
                    parent_block_id=root_block_id,
                    child_ids=desired_ids[j1:j2],
                    block_map=block_map,
                    children_map=children_map,
                    user_id_type=user_id_type,
                    insert_index=start,
                    image_paths=convert.image_paths,
                    file_paths=convert.file_paths,
                )
                offset += (j2 - j1)
        logger.info("局部更新完成: document_id={}", document_id)
        return True


def _block_signature(
    block_id: str,
    block_map: dict[str, dict[str, Any]],
    parser: DocxParser,
) -> str:
    block = block_map.get(block_id)
    if not block:
        return "missing"
    block_type = block.get("block_type")
    if block_type == BLOCK_TYPE_IMAGE:
        token = (block.get("image") or {}).get("token") or ""
        return f"27:{token}"
    if block_type == BLOCK_TYPE_FILE:
        token = (block.get("file") or {}).get("token") or ""
        return f"23:{token}"
    if block_type == BLOCK_TYPE_TABLE:
        table_md = parser.table_markdown(block)
        return f"31:{_hash_text(table_md)}"
    text = parser.collect_text(block_id)
    return f"{block_type}:{_hash_text(text)}"


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _has_duplicate_signatures(signatures: list[str]) -> bool:
    if not signatures:
        return False
    return len(set(signatures)) < len(signatures)


def _unique_anchor_pairs(
    current_sigs: list[str],
    desired_sigs: list[str],
) -> list[tuple[int, int]]:
    current_counts = Counter(current_sigs)
    desired_counts = Counter(desired_sigs)
    current_unique = {
        sig: idx for idx, sig in enumerate(current_sigs) if current_counts[sig] == 1
    }
    desired_unique = {
        sig: idx for idx, sig in enumerate(desired_sigs) if desired_counts[sig] == 1
    }
    anchors = [
        (current_unique[sig], desired_unique[sig])
        for sig in current_unique.keys() & desired_unique.keys()
    ]
    anchors.sort(key=lambda item: item[0])
    return anchors


__all__ = ["DocxPartialUpdateService"]
