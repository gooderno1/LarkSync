from __future__ import annotations

import difflib
import hashlib
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

from src.services.feishu_client import FeishuClient
from src.services.media_uploader import MediaUploadError, MediaUploader
from src.services.transcoder import (
    DocxParser,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_TABLE,
    BLOCK_TYPE_FILE,
    BLOCK_TYPE_TEXT,
)


class DocxServiceError(RuntimeError):
    pass


@dataclass
class ConvertResult:
    first_level_block_ids: list[str]
    blocks: list[dict[str, Any]]
    image_paths: dict[str, Path] = field(default_factory=dict)


@dataclass
class MarkdownSegment:
    kind: str
    value: str


_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")


class DocxService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
        media_uploader: MediaUploader | None = None,
        image_parent_type: str = "docx_image",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")
        self._image_parent_type = image_parent_type
        self._media_uploader = media_uploader or MediaUploader(
            client=self._client,
            base_url=self._base_url,
            default_parent_type=image_parent_type,
        )

    async def replace_document_content(
        self,
        document_id: str,
        markdown: str,
        user_id_type: str = "open_id",
        base_path: str | Path | None = None,
        update_mode: str = "auto",
    ) -> None:
        logger.info(
            "替换文档内容: document_id={} length={}", document_id, len(markdown)
        )
        items = await self.list_blocks(document_id, user_id_type=user_id_type)
        root_block = self._find_root_block(items)
        if not root_block:
            raise DocxServiceError("未找到文档根 Block")

        convert = await self.convert_markdown_with_images(
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
            _summarize_block_types(convert.blocks),
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
            ok = await self._create_from_convert(
                document_id=document_id,
                root_block_id=root_block["block_id"],
                convert=convert,
                user_id_type=user_id_type,
            )
            if not ok:
                raise DocxServiceError("创建块失败，已中止替换")
            logger.info(
                "新内容已创建: document_id={} blocks={}",
                document_id,
                len(convert.blocks),
            )

            if children:
                await self.delete_children(
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

    async def convert_markdown(
        self, markdown: str, user_id_type: str = "open_id"
    ) -> ConvertResult:
        payload = {"content_type": "markdown", "content": markdown}
        response = await self._request_json(
            "POST",
            f"{self._base_url}/open-apis/docx/v1/documents/blocks/convert",
            params={"user_id_type": user_id_type},
            json=payload,
        )
        data = response.get("data")
        if not isinstance(data, dict):
            raise DocxServiceError("转换接口响应缺少 data")
        first_level_block_ids = data.get("first_level_block_ids")
        blocks = data.get("blocks")
        if not isinstance(first_level_block_ids, list) or not isinstance(blocks, list):
            raise DocxServiceError("转换接口响应缺少 blocks 信息")
        return ConvertResult(
            first_level_block_ids=first_level_block_ids,
            blocks=blocks,
        )

    async def convert_markdown_with_images(
        self,
        markdown: str,
        document_id: str,
        user_id_type: str = "open_id",
        base_path: str | Path | None = None,
    ) -> ConvertResult:
        processed_markdown, placeholders, image_paths = self._build_image_placeholders(
            markdown, base_path
        )
        logger.info(
            "解析 Markdown 图片: document_id={} placeholders={}",
            document_id,
            len(placeholders),
        )
        convert = await self.convert_markdown(
            processed_markdown, user_id_type=user_id_type
        )
        if not placeholders:
            return _patch_table_properties(convert, processed_markdown)

        convert = self._replace_placeholders_with_images(
            convert,
            placeholders=placeholders,
            image_paths=image_paths,
        )
        return _patch_table_properties(convert, processed_markdown)

    async def list_blocks(
        self, document_id: str, user_id_type: str = "open_id"
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {"page_size": 500, "user_id_type": user_id_type}
            if page_token:
                params["page_token"] = page_token
            response = await self._request_json(
                "GET",
                f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks",
                params=params,
            )
            data = response.get("data")
            if not isinstance(data, dict):
                raise DocxServiceError("获取块列表响应缺少 data")
            page_items = data.get("items", [])
            if isinstance(page_items, list):
                items.extend(page_items)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
        return items

    async def delete_children(
        self, document_id: str, block_id: str, start_index: int, end_index: int
    ) -> None:
        payload = {"start_index": start_index, "end_index": end_index}
        await self._request_json(
            "DELETE",
            f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete",
            params={"client_token": str(uuid.uuid4()), "document_revision_id": -1},
            json=payload,
        )

    async def get_root_block(
        self, document_id: str, user_id_type: str = "open_id"
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        items = await self.list_blocks(document_id, user_id_type=user_id_type)
        root_block = self._find_root_block(items)
        if not root_block:
            raise DocxServiceError("未找到文档根 Block")
        return root_block, items

    async def _create_from_convert(
        self,
        document_id: str,
        root_block_id: str,
        convert: ConvertResult,
        user_id_type: str,
        insert_index: int = -1,
    ) -> bool:
        error_flag = {"error": False}
        block_map = {block.get("block_id"): block for block in convert.blocks}
        children_map = {
            block.get("block_id"): _extract_children_ids(block)
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
            error_flag=error_flag,
        )
        return not error_flag["error"]

    async def insert_markdown_block(
        self,
        document_id: str,
        root_block_id: str,
        markdown: str,
        *,
        base_path: str | Path | None,
        user_id_type: str = "open_id",
        insert_index: int = -1,
    ) -> int:
        convert = await self.convert_markdown_with_images(
            markdown,
            document_id=document_id,
            user_id_type=user_id_type,
            base_path=base_path,
        )
        convert = self._normalize_convert(convert)
        ok = await self._create_from_convert(
            document_id=document_id,
            root_block_id=root_block_id,
            convert=convert,
            user_id_type=user_id_type,
            insert_index=insert_index,
        )
        if not ok:
            raise DocxServiceError("创建块失败，已中止插入")
        return len(convert.first_level_block_ids)

    async def _create_children_recursive(
        self,
        document_id: str,
        parent_block_id: str,
        child_ids: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
        insert_index: int = -1,
        image_paths: dict[str, Path] | None = None,
        error_flag: dict[str, bool] | None = None,
    ) -> None:
        next_index = insert_index
        for chunk in _chunked(child_ids, 50):
            logger.info(
                "创建子块: document_id={} parent={} size={} types={}",
                document_id,
                parent_block_id,
                len(chunk),
                _summarize_block_types([block_map[child_id] for child_id in chunk]),
            )
            payload = {
                "children": [self._sanitize_block(block_map[child_id]) for child_id in chunk],
            }
            if next_index >= 0:
                payload["index"] = next_index
            image_uploads: list[tuple[int, Path]] = []
            if image_paths:
                for idx, child_id in enumerate(chunk):
                    image_path = image_paths.get(child_id)
                    if image_path:
                        image_uploads.append((idx, image_path))
            if next_index >= 0:
                next_index += len(chunk)
            try:
                response = await self._request_json(
                    "POST",
                    f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
                    params={
                        "client_token": str(uuid.uuid4()),
                        "document_revision_id": -1,
                        "user_id_type": user_id_type,
                    },
                    json=payload,
                )
            except Exception as exc:
                await self._handle_create_children_error(
                    exc,
                    document_id=document_id,
                    parent_block_id=parent_block_id,
                    chunk=chunk,
                    block_map=block_map,
                    children_map=children_map,
                    user_id_type=user_id_type,
                    image_paths=image_paths,
                    insert_index=insert_index,
                    error_flag=error_flag,
                )
                continue
            data = response.get("data") or {}
            created = data.get("children", [])
            if not isinstance(created, list):
                raise DocxServiceError("创建块响应缺少 children")

            if image_uploads:
                for idx, image_path in image_uploads:
                    if idx >= len(created):
                        continue
                    new_id = created[idx].get("block_id")
                    if not new_id:
                        continue
                    try:
                        await self._media_uploader.upload_image(
                            image_path,
                            parent_node=new_id,
                            parent_type=self._image_parent_type,
                        )
                    except MediaUploadError as exc:
                        logger.error(
                            "图片上传失败: document_id={} block_id={} path={} error={}",
                            document_id,
                            new_id,
                            image_path,
                            exc,
                        )

            for old_id, new_block in zip(chunk, created):
                new_id = new_block.get("block_id")
                if not new_id:
                    raise DocxServiceError("创建块响应缺少 block_id")
                old_children = children_map.get(old_id, [])
                if old_children:
                    await self._create_children_recursive(
                        document_id=document_id,
                        parent_block_id=new_id,
                        child_ids=old_children,
                        block_map=block_map,
                        children_map=children_map,
                        user_id_type=user_id_type,
                        insert_index=-1,
                        image_paths=image_paths,
                        error_flag=error_flag,
                    )

    async def _handle_create_children_error(
        self,
        exc: Exception,
        *,
        document_id: str,
        parent_block_id: str,
        chunk: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
        image_paths: dict[str, Path] | None = None,
        insert_index: int = -1,
        error_flag: dict[str, bool] | None = None,
    ) -> None:
        logger.warning(
            "创建子块失败，准备拆分重试: document_id={} parent={} size={} error={}",
            document_id,
            parent_block_id,
            len(chunk),
            exc,
        )
        if len(chunk) <= 1:
            if not chunk:
                return
            block_id = chunk[0]
            block = self._sanitize_block(block_map[block_id])
            logger.error(
                "无效块已跳过: document_id={} parent={} block_id={} block_type={} keys={} payload={}",
                document_id,
                parent_block_id,
                block_id,
                block.get("block_type"),
                sorted(block.keys()),
                _truncate_payload(block),
            )
            if error_flag is not None:
                error_flag["error"] = True
            return
        mid = len(chunk) // 2
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[:mid],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index,
            image_paths=image_paths,
            error_flag=error_flag,
        )
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[mid:],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index if insert_index < 0 else insert_index + mid,
            image_paths=image_paths,
            error_flag=error_flag,
        )

    async def _apply_partial_update(
        self,
        *,
        document_id: str,
        root_block_id: str,
        current_children: list[str],
        current_blocks: list[dict[str, Any]],
        convert: ConvertResult,
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
        if not force and any(
            block.get("block_type") == BLOCK_TYPE_TABLE for block in convert.blocks
        ):
            logger.info("局部更新跳过: 检测到表格块，退回全量覆盖")
            return False

        current_parser = _build_parser(current_blocks)
        desired_parser = _build_parser(convert.blocks)

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
            block.get("block_id"): _extract_children_ids(block)
            for block in convert.blocks
        }

        offset = 0
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            start = i1 + offset
            end = i2 + offset
            if tag in {"delete", "replace"} and end > start:
                await self.delete_children(
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
                )
                offset += (j2 - j1)
        logger.info("局部更新完成: document_id={}", document_id)
        return True

    @staticmethod
    def _sanitize_block(block: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(block)
        cleaned.pop("block_id", None)
        cleaned.pop("parent_id", None)
        cleaned.pop("children", None)
        if cleaned.get("block_type") == BLOCK_TYPE_TABLE:
            table = cleaned.get("table")
            if isinstance(table, dict):
                table = dict(table)
                table.pop("cells", None)
                cleaned["table"] = table
        return cleaned

    @staticmethod
    def _find_root_block(items: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
        for item in items:
            if item.get("block_type") == 1 and not item.get("parent_id"):
                return item
        for item in items:
            if item.get("block_type") == 1:
                return item
        return next(iter(items), None)

    async def _request_json(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = await self._client.request_with_retry(method, url, **kwargs)
        try:
            response.raise_for_status()
        except Exception as exc:
            logger.error(
                "请求失败: {} {} status={} params={} body={}",
                method,
                url,
                response.status_code,
                kwargs.get("params"),
                response.text,
            )
            raise exc
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) != 0:
            logger.error(
                "飞书 API 错误: {} {} code={} msg={} params={}",
                method,
                url,
                payload.get("code"),
                payload.get("msg"),
                kwargs.get("params"),
            )
            raise DocxServiceError(payload.get("msg", "飞书 API 返回错误"))
        if not isinstance(payload, dict):
            raise DocxServiceError("飞书 API 响应格式错误")
        return payload

    @staticmethod
    def _normalize_convert(convert: ConvertResult) -> ConvertResult:
        block_map = {block.get("block_id"): block for block in convert.blocks}
        new_first_level: list[str] = []
        removed = 0
        for block_id in convert.first_level_block_ids:
            block = block_map.get(block_id)
            if block and block.get("block_type") == 1:
                removed += 1
                children = block.get("children") or []
                new_first_level.extend(children)
            else:
                new_first_level.append(block_id)
        if removed:
            logger.warning(
                "转换结果包含根块，已展开 children: removed={}",
                removed,
            )
            new_blocks = [block for block in convert.blocks if block.get("block_type") != 1]
            return ConvertResult(
                first_level_block_ids=new_first_level,
                blocks=new_blocks,
                image_paths=dict(convert.image_paths),
            )
        return convert

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close:
            await close()

    @staticmethod
    def _split_markdown_images(markdown: str) -> list[MarkdownSegment]:
        segments: list[MarkdownSegment] = []
        cursor = 0
        for match in _IMAGE_PATTERN.finditer(markdown):
            before = markdown[cursor : match.start()]
            if before:
                _append_text_segment(segments, before)
            raw = match.group(0)
            ref = _normalize_image_ref(match.group(1))
            if _is_remote_image(ref):
                _append_text_segment(segments, raw)
            else:
                segments.append(MarkdownSegment(kind="image", value=ref))
            cursor = match.end()
        tail = markdown[cursor:]
        if tail:
            _append_text_segment(segments, tail)
        if not segments:
            segments.append(MarkdownSegment(kind="text", value=markdown))
        return segments

    def _build_image_placeholders(
        self, markdown: str, base_path: str | Path | None
    ) -> tuple[str, dict[str, str], dict[str, Path]]:
        processed = markdown
        placeholders: dict[str, str] = {}
        image_paths: dict[str, Path] = {}
        for match in _IMAGE_PATTERN.finditer(markdown):
            raw = match.group(0)
            ref = _normalize_image_ref(match.group(1))
            if _is_remote_image(ref):
                continue
            image_path = self._resolve_image_path(ref, base_path)
            if not image_path.exists() or not image_path.is_file():
                processed = processed.replace(raw, f"[图片缺失: {ref}]")
                continue
            placeholder = f"[[LARKSYNC_IMAGE:{_hash_text(str(image_path))}]]"
            placeholders[placeholder] = ref
            image_paths[placeholder] = image_path
            processed = processed.replace(raw, placeholder)
        return processed, placeholders, image_paths

    def _replace_placeholders_with_images(
        self,
        convert: ConvertResult,
        *,
        placeholders: dict[str, str],
        image_paths: dict[str, Path],
    ) -> ConvertResult:
        if not placeholders:
            return convert
        block_map = {block.get("block_id"): block for block in convert.blocks}
        parser = DocxParser(convert.blocks)
        new_blocks: list[dict[str, Any]] = []
        replaced: dict[str, str] = {}
        image_block_paths: dict[str, Path] = {}
        for block_id in convert.first_level_block_ids:
            block = block_map.get(block_id)
            if not block:
                continue
            text = parser.text_from_block(block).strip()
            if (
                block.get("block_type") == BLOCK_TYPE_TEXT
                and text in placeholders
            ):
                image_block_id = f"img_{uuid.uuid4().hex}"
                replaced[block_id] = image_block_id
                image_block_paths[image_block_id] = image_paths[text]
                new_blocks.append(
                    {"block_id": image_block_id, "block_type": 27, "image": {}}
                )
            else:
                new_blocks.append(block)

        if not replaced:
            convert.image_paths.update(image_block_paths)
            return convert

        new_first_level = [
            replaced.get(block_id, block_id) for block_id in convert.first_level_block_ids
        ]
        filtered_blocks = [
            block for block in convert.blocks if block.get("block_id") not in replaced
        ]
        filtered_blocks.extend(
            block for block in new_blocks if block.get("block_id") in replaced.values()
        )
        convert.image_paths.update(image_block_paths)
        return ConvertResult(
            first_level_block_ids=new_first_level,
            blocks=filtered_blocks,
            image_paths=convert.image_paths,
        )

    @staticmethod
    def _resolve_image_path(ref: str, base_path: str | Path | None) -> Path:
        normalized = ref
        if ref.lower().startswith("file://"):
            normalized = ref[7:]
        path = Path(normalized)
        if not path.is_absolute() and base_path:
            base = Path(base_path)
            if base.is_file():
                base = base.parent
            path = base / path
        return path



def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _append_text_segment(segments: list[MarkdownSegment], text: str) -> None:
    if segments and segments[-1].kind == "text":
        segments[-1].value += text
    else:
        segments.append(MarkdownSegment(kind="text", value=text))


def _normalize_image_ref(raw: str) -> str:
    ref = raw.strip()
    if ref.startswith("<") and ref.endswith(">"):
        ref = ref[1:-1].strip()
    if " " in ref:
        ref = ref.split()[0]
    return ref


def _is_remote_image(ref: str) -> bool:
    lowered = ref.lower()
    return lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith(
        "data:"
    )


def _summarize_block_types(blocks: Iterable[dict[str, Any]]) -> dict[int | None, int]:
    summary: dict[int | None, int] = {}
    for block in blocks:
        block_type = block.get("block_type")
        if not isinstance(block_type, int):
            block_type = None
        summary[block_type] = summary.get(block_type, 0) + 1
    return summary


def _truncate_payload(payload: dict[str, Any], limit: int = 800) -> str:
    try:
        text = str(payload)
    except Exception:
        return "<unprintable>"
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _build_parser(blocks: list[dict[str, Any]]) -> DocxParser:
    return DocxParser(blocks)


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


def _extract_children_ids(block: dict[str, Any]) -> list[str]:
    children = block.get("children") or []
    if children:
        return list(children)
    if block.get("block_type") == BLOCK_TYPE_TABLE:
        table = block.get("table") or {}
        cells = table.get("cells") or []
        flattened = _flatten_table_cells(cells)
        if flattened:
            return flattened
    return []


def _flatten_table_cells(cells: object) -> list[str]:
    if not isinstance(cells, list):
        return []
    flattened: list[str] = []
    for cell in cells:
        if isinstance(cell, list):
            for inner in cell:
                if isinstance(inner, str):
                    flattened.append(inner)
        elif isinstance(cell, str):
            flattened.append(cell)
    return flattened


def _has_duplicate_signatures(signatures: list[str]) -> bool:
    if not signatures:
        return False
    return len(set(signatures)) < len(signatures)


def _unique_anchor_pairs(
    current_sigs: list[str], desired_sigs: list[str]
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


def _patch_table_properties(convert: ConvertResult, markdown: str) -> ConvertResult:
    specs = _extract_markdown_table_specs(markdown)
    if not specs:
        return convert
    spec_index = 0
    for block in convert.blocks:
        if block.get("block_type") != BLOCK_TYPE_TABLE:
            continue
        table = block.get("table") or {}
        prop = table.get("property") or {}
        row_size = _safe_int(prop.get("row_size"))
        col_size = _safe_int(prop.get("column_size"))
        if row_size > 0 and col_size > 0:
            continue
        if spec_index >= len(specs):
            continue
        rows, cols = specs[spec_index]
        spec_index += 1
        prop = dict(prop)
        if row_size <= 0:
            prop["row_size"] = rows
        if col_size <= 0:
            prop["column_size"] = cols
        table = dict(table)
        table["property"] = prop
        block["table"] = table
        logger.info("补齐表格属性: rows={} cols={}", rows, cols)
    return convert


def _extract_markdown_table_specs(markdown: str) -> list[tuple[int, int]]:
    tables: list[tuple[int, int]] = []
    lines = markdown.splitlines()
    in_code_block = False
    i = 0
    while i + 1 < len(lines):
        line = lines[i].strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            i += 1
            continue
        if in_code_block:
            i += 1
            continue
        if "|" not in line:
            i += 1
            continue
        sep = lines[i + 1].strip()
        if not _is_table_separator(sep):
            i += 1
            continue
        cols = _count_table_columns(line)
        if cols <= 0:
            i += 1
            continue
        rows = 1
        j = i + 2
        while j < len(lines):
            row_line = lines[j].strip()
            if row_line.startswith("```"):
                break
            if "|" not in row_line:
                break
            if _is_table_separator(row_line):
                break
            rows += 1
            j += 1
        tables.append((rows, cols))
        i = j
    return tables


def _is_table_separator(line: str) -> bool:
    if "|" not in line:
        return False
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    if not parts:
        return False
    for part in parts:
        if not part:
            return False
        body = part.replace(":", "")
        if len(body) < 3:
            return False
        if any(ch != "-" for ch in body):
            return False
    return True


def _count_table_columns(line: str) -> int:
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    return len(parts)


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
