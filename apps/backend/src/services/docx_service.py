from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

from src.services.feishu_client import FeishuClient
from src.services.media_uploader import MediaUploadError, MediaUploader


class DocxServiceError(RuntimeError):
    pass


@dataclass
class ConvertResult:
    first_level_block_ids: list[str]
    blocks: list[dict[str, Any]]


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
        await self._create_from_convert(
            document_id=document_id,
            root_block_id=root_block["block_id"],
            convert=convert,
            user_id_type=user_id_type,
        )
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
        segments = self._split_markdown_images(markdown)
        image_count = sum(1 for segment in segments if segment.kind == "image")
        logger.info(
            "解析 Markdown 图片: document_id={} segments={} images={}",
            document_id,
            len(segments),
            image_count,
        )
        if image_count == 0:
            return await self.convert_markdown(markdown, user_id_type=user_id_type)

        first_level_block_ids: list[str] = []
        blocks: list[dict[str, Any]] = []
        for segment in segments:
            if segment.kind == "text":
                if not segment.value.strip():
                    continue
                convert = await self.convert_markdown(
                    segment.value, user_id_type=user_id_type
                )
                first_level_block_ids.extend(convert.first_level_block_ids)
                blocks.extend(convert.blocks)
                continue
            image_path = self._resolve_image_path(segment.value, base_path)
            try:
                image_token = await self._media_uploader.upload_image(
                    image_path,
                    parent_node=document_id,
                    parent_type=self._image_parent_type,
                )
                image_block_id = f"img_{uuid.uuid4().hex}"
                first_level_block_ids.append(image_block_id)
                blocks.append(
                    {
                        "block_id": image_block_id,
                        "block_type": 27,
                        "image": {"token": image_token},
                    }
                )
            except MediaUploadError:
                placeholder = f"[图片缺失: {segment.value}]"
                convert = await self.convert_markdown(
                    placeholder, user_id_type=user_id_type
                )
                first_level_block_ids.extend(convert.first_level_block_ids)
                blocks.extend(convert.blocks)

        return ConvertResult(
            first_level_block_ids=first_level_block_ids,
            blocks=blocks,
        )

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

    async def _create_from_convert(
        self,
        document_id: str,
        root_block_id: str,
        convert: ConvertResult,
        user_id_type: str,
    ) -> None:
        block_map = {block.get("block_id"): block for block in convert.blocks}
        children_map = {
            block.get("block_id"): block.get("children", [])
            for block in convert.blocks
        }
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=root_block_id,
            child_ids=convert.first_level_block_ids,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
        )

    async def _create_children_recursive(
        self,
        document_id: str,
        parent_block_id: str,
        child_ids: list[str],
        block_map: dict[str, dict[str, Any]],
        children_map: dict[str, list[str]],
        user_id_type: str,
    ) -> None:
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
                "index": -1,
            }
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
                )
                continue
            data = response.get("data") or {}
            created = data.get("children", [])
            if not isinstance(created, list):
                raise DocxServiceError("创建块响应缺少 children")

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
            return
        mid = len(chunk) // 2
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[:mid],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
        )
        await self._create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=chunk[mid:],
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
        )

    @staticmethod
    def _sanitize_block(block: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(block)
        cleaned.pop("block_id", None)
        cleaned.pop("parent_id", None)
        cleaned.pop("children", None)
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
