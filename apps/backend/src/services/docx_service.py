from __future__ import annotations

import base64
import binascii
import hashlib
import re
import tempfile
import unicodedata
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

from loguru import logger

from src.services.docx_block_create_service import (
    DocxBlockCreateService,
    build_create_chunks as _build_create_chunks,
)
from src.services.docx_content_write_service import DocxContentWriteService
from src.services.docx_markdown_convert_helper import (
    compile_placeholder_pattern as _compile_placeholder_pattern,
    find_placeholders as _find_placeholders,
    has_text_elements as _has_text_elements,
    normalize_markdown_for_convert as _normalize_markdown_for_convert,
    plain_text_block as _plain_text_block,
    replace_continuation_placeholders as _replace_continuation_placeholders,
    set_block_plain_text as _set_block_plain_text,
    strip_placeholders_from_block as _strip_placeholders_from_block,
)
from src.services.docx_markdown_asset_service import DocxMarkdownAssetService
from src.services.docx_partial_update_service import DocxPartialUpdateService
from src.services.docx_table_runtime_service import DocxTableRuntimeService
from src.services.feishu_client import FeishuClient
from src.services.file_uploader import FileUploader
from src.services.media_uploader import MediaUploader
from src.services.transcoder import (
    DocxParser,
    BLOCK_TYPE_CODE,
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
    file_paths: dict[str, Path] = field(default_factory=dict)


@dataclass
class MarkdownSegment:
    kind: str
    value: str


@dataclass(frozen=True)
class MarkdownTableSpec:
    rows: int
    cols: int
    column_width: list[int]


_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
_HTML_IMAGE_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
_HTML_IMAGE_SRC_PATTERN = re.compile(
    r"""\bsrc\s*=\s*(?P<quote>["'])(?P<src>.*?)(?P=quote)""",
    re.IGNORECASE | re.DOTALL,
)
_IMAGE_DISPLAY_MAX_WIDTH = 820
TABLE_BLOCK_CREATE_MAX_ROWS = 9
_TABLE_COLUMN_MIN_WIDTH = 120
_TABLE_COLUMN_MAX_WIDTH = 600
_TABLE_SINGLE_COLUMN_WIDTH = 600
_TABLE_MAX_TOTAL_WIDTH = 1080
_TABLE_PREFERRED_TOTAL_WIDTH = 732
_EMPTY_CODE_BLOCK_PLACEHOLDER = "\u200b"
_FIGURE_START_PATTERN = re.compile(
    r"<!--\s*FIGURE:(?P<id>[\w.-]+):START\s*-->",
    re.IGNORECASE,
)
_FIGURE_END_PATTERN = re.compile(
    r"<!--\s*FIGURE:(?P<id>[\w.-]+):END\s*-->",
    re.IGNORECASE,
)
_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*]\(([^)]+)\)")


def _build_placeholder_text_elements() -> list[dict[str, Any]]:
    return [
        {
            "text_run": {
                "content": _EMPTY_CODE_BLOCK_PLACEHOLDER,
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


class DocxService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
        media_uploader: MediaUploader | None = None,
        file_uploader: FileUploader | None = None,
        image_parent_type: str = "docx_image",
        file_parent_type: str = "docx_file",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")
        self._image_parent_type = image_parent_type
        self._file_parent_type = file_parent_type
        self._media_uploader = media_uploader or MediaUploader(
            client=self._client,
            base_url=self._base_url,
            default_parent_type=image_parent_type,
        )
        self._file_uploader = file_uploader or FileUploader(
            client=self._client,
            base_url=self._base_url,
        )
        self._markdown_asset_service = DocxMarkdownAssetService(
            normalize_image_ref=_normalize_image_ref,
            is_remote_image=_is_remote_image,
            is_remote_link=_is_remote_link,
            hash_text=_hash_text,
            find_figure_id_for_offset=_find_figure_id_for_offset,
            find_local_figure_asset=_find_local_figure_asset,
            extract_figure_id_from_image_ref=_extract_figure_id_from_image_ref,
            write_data_image_to_temp=_write_data_image_to_temp,
            compile_placeholder_pattern=_compile_placeholder_pattern,
            find_placeholders=_find_placeholders,
            strip_placeholders_from_block=_strip_placeholders_from_block,
            set_block_plain_text=_set_block_plain_text,
            has_text_elements=_has_text_elements,
        )
        self._table_runtime_service = DocxTableRuntimeService(
            convert_markdown=self.convert_markdown,
            normalize_convert=self._normalize_convert,
            create_children_recursive=self._create_children_recursive,
            insert_table_row=self.insert_table_row,
            list_blocks=self.list_blocks,
            try_delete_children=self._try_delete_children,
            split_large_markdown_tables_for_convert=_split_large_markdown_tables_for_convert,
            patch_table_properties=_patch_table_properties,
            extract_children_ids=_extract_children_ids,
            flatten_table_cells=_flatten_table_cells,
            table_dimensions=_table_dimensions,
            plain_text_block=_plain_text_block,
        )
        self._partial_update_service = DocxPartialUpdateService(
            delete_children=self.delete_children,
            create_children_recursive=self._create_children_recursive,
            extract_children_ids=_extract_children_ids,
        )
        self._block_create_service = DocxBlockCreateService(
            request_json=self._request_json,
            sanitize_block=self._sanitize_block,
            replace_image_block=self._replace_image_block,
            replace_file_block=self._replace_file_block,
            populate_table_cells=self._populate_table_cells,
            fallback_table_block_without_code=self._fallback_table_block_without_code,
            summarize_block_types=_summarize_block_types,
            truncate_payload=_truncate_payload,
            media_uploader=self._media_uploader,
            file_uploader=self._file_uploader,
            base_url=self._base_url,
            image_parent_type=self._image_parent_type,
            file_parent_type=self._file_parent_type,
            service_error_cls=DocxServiceError,
        )
        self._content_write_service = DocxContentWriteService(
            list_blocks=self.list_blocks,
            find_root_block=self._find_root_block,
            convert_markdown_with_images=self.convert_markdown_with_images,
            normalize_convert=self._normalize_convert,
            apply_partial_update=self._apply_partial_update,
            create_children_recursive=self._create_children_recursive,
            delete_children=self.delete_children,
            summarize_block_types=_summarize_block_types,
            extract_children_ids=_extract_children_ids,
            service_error_cls=DocxServiceError,
        )

    async def replace_document_content(
        self,
        document_id: str,
        markdown: str,
        user_id_type: str = "open_id",
        base_path: str | Path | None = None,
        update_mode: str = "auto",
    ) -> None:
        await self._content_write_service.replace_document_content(
            document_id=document_id,
            markdown=markdown,
            user_id_type=user_id_type,
            base_path=base_path,
            update_mode=update_mode,
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
        normalized_markdown = _normalize_markdown_for_convert(markdown)
        processed_markdown, placeholders, image_paths = self._build_image_placeholders(
            normalized_markdown, base_path
        )
        processed_markdown, file_placeholders, file_paths = self._build_file_placeholders(
            processed_markdown, base_path
        )
        logger.info(
            "解析 Markdown 资源: document_id={} image_placeholders={} file_placeholders={}",
            document_id,
            len(placeholders),
            len(file_placeholders),
        )
        convert = await self.convert_markdown(
            processed_markdown, user_id_type=user_id_type
        )
        convert = _replace_continuation_placeholders(convert)
        if not placeholders and not file_placeholders:
            return _patch_table_properties(convert, processed_markdown)

        convert = self._replace_placeholders_with_images(
            convert,
            placeholders=placeholders,
            image_paths=image_paths,
            file_placeholders=file_placeholders,
            file_paths=file_paths,
        )
        return _patch_table_properties(convert, processed_markdown)

    async def list_blocks(
        self, document_id: str, user_id_type: str = "open_id"
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {"page_size": 200, "user_id_type": user_id_type}
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
        if end_index <= start_index:
            return
        chunk_size = 50
        current_end = end_index
        while current_end > start_index:
            current_start = max(start_index, current_end - chunk_size)
            payload = {"start_index": current_start, "end_index": current_end}
            await self._request_json(
                "DELETE",
                f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete",
                params={"client_token": str(uuid.uuid4()), "document_revision_id": -1},
                json=payload,
            )
            current_end = current_start

    async def _try_delete_children(
        self,
        document_id: str,
        block_id: str,
        start_index: int,
        end_index: int,
    ) -> bool:
        try:
            await self.delete_children(
                document_id=document_id,
                block_id=block_id,
                start_index=start_index,
                end_index=end_index,
            )
            return True
        except Exception as exc:
            logger.warning(
                "清理子块失败，继续保留当前内容: document_id={} block_id={} range={}..{} error={}",
                document_id,
                block_id,
                start_index,
                end_index,
                exc,
            )
            return False

    async def insert_table_row(
        self,
        document_id: str,
        table_block_id: str,
        *,
        row_index: int = -1,
        user_id_type: str = "open_id",
    ) -> None:
        await self._request_json(
            "PATCH",
            f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{table_block_id}",
            params={"document_revision_id": -1, "user_id_type": user_id_type},
            json={"insert_table_row": {"row_index": row_index}},
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
        return await self._content_write_service.create_from_convert(
            document_id=document_id,
            root_block_id=root_block_id,
            convert=convert,
            user_id_type=user_id_type,
            insert_index=insert_index,
        )

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
        return await self._content_write_service.insert_markdown_block(
            document_id=document_id,
            root_block_id=root_block_id,
            markdown=markdown,
            base_path=base_path,
            user_id_type=user_id_type,
            insert_index=insert_index,
        )

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
        file_paths: dict[str, Path] | None = None,
        error_flag: dict[str, bool] | None = None,
    ) -> None:
        await self._block_create_service.create_children_recursive(
            document_id=document_id,
            parent_block_id=parent_block_id,
            child_ids=child_ids,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            insert_index=insert_index,
            image_paths=image_paths,
            file_paths=file_paths,
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
        file_paths: dict[str, Path] | None = None,
        insert_index: int = -1,
        error_flag: dict[str, bool] | None = None,
        _rate_limit_retry: int = 0,
    ) -> None:
        await self._block_create_service.handle_create_children_error(
            exc,
            document_id=document_id,
            parent_block_id=parent_block_id,
            chunk=chunk,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            image_paths=image_paths,
            file_paths=file_paths,
            insert_index=insert_index,
            error_flag=error_flag,
            rate_limit_retry=_rate_limit_retry,
        )

    async def _fallback_table_block_without_code(
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
        return await self._table_runtime_service.fallback_table_block_without_code(
            document_id=document_id,
            parent_block_id=parent_block_id,
            table_block_id=table_block_id,
            block_map=block_map,
            user_id_type=user_id_type,
            insert_index=insert_index,
            error_flag=error_flag,
        )

    async def _populate_table_cells(
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
        await self._table_runtime_service.populate_table_cells(
            document_id=document_id,
            table_block=table_block,
            source_table_block=source_table_block,
            block_map=block_map,
            children_map=children_map,
            user_id_type=user_id_type,
            image_paths=image_paths,
            file_paths=file_paths,
            error_flag=error_flag,
        )

    async def _ensure_table_row_capacity(
        self,
        *,
        document_id: str,
        table_block: dict[str, Any],
        current_rows: int,
        desired_rows: int,
        user_id_type: str,
        error_flag: dict[str, bool] | None = None,
    ) -> list[str]:
        return await self._table_runtime_service.ensure_table_row_capacity(
            document_id=document_id,
            table_block=table_block,
            current_rows=current_rows,
            desired_rows=desired_rows,
            user_id_type=user_id_type,
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
        return await self._partial_update_service.apply_partial_update(
            document_id=document_id,
            root_block_id=root_block_id,
            current_children=current_children,
            current_blocks=current_blocks,
            convert=convert,
            user_id_type=user_id_type,
            force=force,
        )

    @staticmethod
    def _sanitize_block(block: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(block)
        cleaned.pop("block_id", None)
        cleaned.pop("parent_id", None)
        cleaned.pop("children", None)
        if cleaned.get("block_type") == BLOCK_TYPE_CODE:
            code = cleaned.get("code")
            if isinstance(code, dict):
                code = dict(code)
                elements = code.get("elements")
                if not isinstance(elements, list) or not elements:
                    code["elements"] = _build_placeholder_text_elements()
                cleaned["code"] = code
        if cleaned.get("block_type") == BLOCK_TYPE_TABLE:
            table = cleaned.get("table")
            if isinstance(table, dict):
                table = dict(table)
                table.pop("cells", None)
                prop = table.get("property")
                if isinstance(prop, dict):
                    prop = dict(prop)
                    prop.pop("merge_info", None)
                    row_size = _safe_int(prop.get("row_size"))
                    if row_size > TABLE_BLOCK_CREATE_MAX_ROWS:
                        prop["row_size"] = TABLE_BLOCK_CREATE_MAX_ROWS
                    column_width = _normalize_column_widths(
                        prop.get("column_width"),
                        _safe_int(prop.get("column_size")),
                    )
                    if column_width:
                        prop["column_width"] = column_width
                    else:
                        prop.pop("column_width", None)
                    table["property"] = prop
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

    async def _replace_image_block(
        self,
        *,
        document_id: str,
        block_id: str,
        token: str,
        image_path: Path | None = None,
        user_id_type: str,
    ) -> None:
        replace_image: dict[str, Any] = {"token": token}
        display_size = _get_image_display_size(image_path)
        if display_size is not None:
            replace_image["width"], replace_image["height"] = display_size
        await self._request_json(
            "PATCH",
            f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
            params={"document_revision_id": -1, "user_id_type": user_id_type},
            json={"replace_image": replace_image},
        )

    async def _replace_file_block(
        self,
        *,
        document_id: str,
        block_id: str,
        token: str,
        user_id_type: str,
    ) -> None:
        await self._request_json(
            "PATCH",
            f"{self._base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
            params={"document_revision_id": -1, "user_id_type": user_id_type},
            json={"replace_file": {"token": token}},
        )

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
                file_paths=dict(convert.file_paths),
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
        return self._markdown_asset_service.build_image_placeholders(markdown, base_path)

    def _build_file_placeholders(
        self, markdown: str, base_path: str | Path | None
    ) -> tuple[str, dict[str, str], dict[str, Path]]:
        return self._markdown_asset_service.build_file_placeholders(markdown, base_path)

    def _resolve_html_image_path(
        self,
        *,
        ref: str,
        markdown: str,
        offset: int,
        base_path: str | Path | None,
    ) -> Path | None:
        return self._markdown_asset_service.resolve_html_image_path(
            ref=ref,
            markdown=markdown,
            offset=offset,
            base_path=base_path,
        )

    def _resolve_markdown_image_path(
        self, ref: str, base_path: str | Path | None
    ) -> Path:
        return self._markdown_asset_service.resolve_markdown_image_path(ref, base_path)

    def _replace_placeholders_with_images(
        self,
        convert: ConvertResult,
        *,
        placeholders: dict[str, str],
        image_paths: dict[str, Path],
        file_placeholders: dict[str, str] | None = None,
        file_paths: dict[str, Path] | None = None,
    ) -> ConvertResult:
        return self._markdown_asset_service.replace_placeholders_with_images(
            convert,
            placeholders=placeholders,
            image_paths=image_paths,
            file_placeholders=file_placeholders,
            file_paths=file_paths,
        )

    @staticmethod
    def _resolve_image_path(ref: str, base_path: str | Path | None) -> Path:
        return DocxMarkdownAssetService.resolve_image_path(ref, base_path)

def _append_text_segment(segments: list[MarkdownSegment], text: str) -> None:
    if segments and segments[-1].kind == "text":
        segments[-1].value += text
    else:
        segments.append(MarkdownSegment(kind="text", value=text))


def _normalize_image_ref(raw: str) -> str:
    ref = raw.strip()
    if ref.startswith("<") and ref.endswith(">"):
        ref = ref[1:-1].strip()
    ref = re.sub(r"""\s+(?:"[^"]*"|'[^']*'|\([^()]*\))\s*$""", "", ref)
    return ref


def _is_remote_image(ref: str) -> bool:
    lowered = ref.lower()
    return _is_remote_link(ref) or lowered.startswith("data:")


def _is_remote_link(ref: str) -> bool:
    lowered = ref.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("tel:")
        or lowered.startswith("#")
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


def _table_dimensions(block: dict[str, Any], cell_count: int = 0) -> tuple[int, int]:
    table = block.get("table") or {}
    prop = table.get("property") or {}
    rows = _safe_int(prop.get("row_size"))
    cols = _safe_int(prop.get("column_size"))
    cells = table.get("cells")
    if (rows <= 0 or cols <= 0) and isinstance(cells, list) and cells:
        if all(isinstance(row, list) for row in cells):
            rows = rows if rows > 0 else len(cells)
            cols = cols if cols > 0 else max(
                (len(row) for row in cells if isinstance(row, list)),
                default=0,
            )
        elif all(isinstance(cell, str) for cell in cells):
            grouped = _group_cells_by_row_token(cells)
            if grouped:
                rows = rows if rows > 0 else len(grouped)
                cols = cols if cols > 0 else max(
                    (len(row) for row in grouped),
                    default=0,
                )
    if rows <= 0 and cols > 0 and cell_count > 0:
        rows = (cell_count + cols - 1) // cols
    if cols <= 0 and rows > 0 and cell_count > 0:
        cols = (cell_count + rows - 1) // rows
    return rows, cols


def _patch_table_properties(convert: ConvertResult, markdown: str) -> ConvertResult:
    specs = _extract_markdown_table_specs(markdown)
    table_ids = _ordered_table_block_ids(convert)
    specs_by_block_id = {
        block_id: specs[idx]
        for idx, block_id in enumerate(table_ids)
        if idx < len(specs)
    }
    for block in convert.blocks:
        if block.get("block_type") != BLOCK_TYPE_TABLE:
            continue
        block_id = block.get("block_id")
        spec = specs_by_block_id.get(block_id) if isinstance(block_id, str) else None
        table = block.get("table") or {}
        prop = table.get("property") or {}
        row_size = _safe_int(prop.get("row_size"))
        col_size = _safe_int(prop.get("column_size"))
        updated = False

        if (row_size <= 0 or col_size <= 0) and spec is not None:
            rows, cols = spec.rows, spec.cols
            prop = dict(prop)
            if row_size <= 0:
                prop["row_size"] = rows
                row_size = rows
                updated = True
            if col_size <= 0:
                prop["column_size"] = cols
                col_size = cols
                updated = True
            logger.info("补齐表格属性: rows={} cols={}", rows, cols)

        existing_width = _normalize_column_widths(prop.get("column_width"), col_size)
        column_width: list[int] = []
        if spec is not None and spec.cols == col_size:
            column_width = list(spec.column_width)
        elif not existing_width and col_size > 0:
            column_width = _default_table_column_widths(col_size)
        if column_width and existing_width != column_width:
            prop = dict(prop)
            prop["column_width"] = column_width
            updated = True

        cells = table.get("cells")
        if isinstance(cells, list) and cells:
            if row_size > 0 and col_size > 0 and all(isinstance(cell, str) for cell in cells):
                if len(cells) >= row_size * col_size:
                    matrix: list[list[str]] = []
                    for r in range(row_size):
                        start = r * col_size
                        matrix.append(cells[start:start + col_size])
                    table = dict(table)
                    table["cells"] = matrix
                    updated = True
            elif all(isinstance(cell, str) for cell in cells):
                matrix = _group_cells_by_row_token(cells)
                if matrix:
                    table = dict(table)
                    table["cells"] = matrix
                    row_size = len(matrix)
                    col_size = max((len(row) for row in matrix), default=0)
                    prop = dict(prop)
                    if row_size > 0 and not prop.get("row_size"):
                        prop["row_size"] = row_size
                        updated = True
                    if col_size > 0 and not prop.get("column_size"):
                        prop["column_size"] = col_size
                        updated = True

        if updated:
            table = dict(table)
            table["property"] = prop
            block["table"] = table
    return convert


def _ordered_table_block_ids(convert: ConvertResult) -> list[str]:
    block_map = {
        block_id: block
        for block in convert.blocks
        if isinstance((block_id := block.get("block_id")), str)
    }
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(block_id: str) -> None:
        if block_id in visited:
            return
        visited.add(block_id)
        block = block_map.get(block_id)
        if not block:
            return
        if block.get("block_type") == BLOCK_TYPE_TABLE:
            ordered.append(block_id)
        for child_id in _extract_children_ids(block):
            if isinstance(child_id, str):
                visit(child_id)

    for block_id in convert.first_level_block_ids:
        if isinstance(block_id, str):
            visit(block_id)
    for block_id in block_map:
        visit(block_id)
    return ordered


def _group_cells_by_row_token(cells: list[str]) -> list[list[str]]:
    row_order: list[str] = []
    rows: dict[str, list[str]] = {}
    for cell in cells:
        if not cell.startswith("row") or "col" not in cell:
            return []
        try:
            row_token, col_token = cell[3:].split("col", 1)
        except ValueError:
            return []
        if row_token not in rows:
            row_order.append(row_token)
            rows[row_token] = []
        rows[row_token].append(f"row{row_token}col{col_token}")
    return [rows[row] for row in row_order]


def _split_large_markdown_tables_for_convert(
    markdown: str,
    *,
    max_rows: int = TABLE_BLOCK_CREATE_MAX_ROWS,
) -> str:
    if max_rows < 2 or "|" not in markdown:
        return markdown
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n")
    trailing_newline = normalized.endswith("\n")
    lines = normalized.split("\n")
    if trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    output: list[str] = []
    in_code_block = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            output.append(line)
            i += 1
            continue
        if in_code_block or i + 1 >= len(lines) or "|" not in line:
            output.append(line)
            i += 1
            continue
        sep = lines[i + 1].strip()
        if not _is_table_separator(sep):
            output.append(line)
            i += 1
            continue

        header = line
        separator = lines[i + 1]
        body: list[str] = []
        j = i + 2
        while j < len(lines):
            row_line = lines[j]
            row_stripped = row_line.strip()
            if row_stripped.startswith("```"):
                break
            if "|" not in row_line:
                break
            if _is_table_separator(row_stripped):
                break
            body.append(row_line)
            j += 1

        rows = 1 + len(body)
        if rows <= max_rows:
            output.extend([header, separator, *body])
            i = j
            continue

        body_limit = max_rows - 1
        for start in range(0, len(body), body_limit):
            if start > 0:
                output.append("")
            output.extend([header, separator, *body[start:start + body_limit]])
        i = j

    result = "\n".join(output)
    if trailing_newline:
        result += "\n"
    return result


def _extract_markdown_table_specs(markdown: str) -> list[MarkdownTableSpec]:
    tables: list[MarkdownTableSpec] = []
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
        table_lines = [lines[i], lines[i + 1]]
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
            table_lines.append(lines[j])
            j += 1
        tables.append(
            MarkdownTableSpec(
                rows=rows,
                cols=cols,
                column_width=_estimate_table_column_widths(table_lines, cols),
            )
        )
        i = j
    return tables


def has_markdown_table_exceeding_create_limit(
    markdown: str,
    *,
    max_rows: int = TABLE_BLOCK_CREATE_MAX_ROWS,
) -> bool:
    return any(spec.rows > max_rows for spec in _extract_markdown_table_specs(markdown))


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
    return len(_parse_markdown_table_cells(line))


def _parse_markdown_table_cells(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def _estimate_table_column_widths(table_lines: list[str], cols: int) -> list[int]:
    if cols <= 0:
        return []
    if cols == 1:
        return [_TABLE_SINGLE_COLUMN_WIDTH]
    max_units = [0] * cols
    for line in table_lines:
        stripped = line.strip()
        if _is_table_separator(stripped):
            continue
        cells = _parse_markdown_table_cells(line)
        for idx in range(min(cols, len(cells))):
            max_units[idx] = max(max_units[idx], _display_units(cells[idx]))

    widths = [
        max(
            _TABLE_COLUMN_MIN_WIDTH,
            min(_TABLE_COLUMN_MAX_WIDTH, int(units * 7 + 48)),
        )
        for units in max_units
    ]
    target_total = _table_target_total_width(cols)
    total = sum(widths)
    if total < target_total:
        widths = _expand_table_column_widths(widths, target_total)
    elif total > target_total:
        widths = _fit_table_column_widths(widths, target_total)
    return widths


def _table_target_total_width(cols: int) -> int:
    preferred_total = min(_TABLE_PREFERRED_TOTAL_WIDTH, _TABLE_MAX_TOTAL_WIDTH)
    return max(preferred_total, _TABLE_COLUMN_MIN_WIDTH * cols)


def _expand_table_column_widths(widths: list[int], target_total: int) -> list[int]:
    if not widths:
        return []
    total = sum(widths)
    if total >= target_total:
        return list(widths)

    extra = target_total - total
    flexible = [max(1, width - _TABLE_COLUMN_MIN_WIDTH) for width in widths]
    flexible_total = sum(flexible)
    if flexible_total <= 0:
        return list(widths)

    raw_widths = [
        width + (extra * flex / flexible_total)
        for width, flex in zip(widths, flexible)
    ]
    expanded = [int(width) for width in raw_widths]
    remainder = target_total - sum(expanded)
    if remainder > 0:
        fractions = sorted(
            (
                (raw_widths[idx] - expanded[idx], idx)
                for idx in range(len(expanded))
            ),
            reverse=True,
        )
        for _fraction, idx in fractions[:remainder]:
            expanded[idx] += 1
    return expanded


def _fit_table_column_widths(widths: list[int], target_total: int) -> list[int]:
    if not widths:
        return []
    min_total = _TABLE_COLUMN_MIN_WIDTH * len(widths)
    if target_total <= min_total:
        return [_TABLE_COLUMN_MIN_WIDTH] * len(widths)
    total = sum(widths)
    if total <= target_total:
        return list(widths)

    flexible = [max(0, width - _TABLE_COLUMN_MIN_WIDTH) for width in widths]
    flexible_total = sum(flexible)
    if flexible_total <= 0:
        return list(widths)

    available = target_total - min_total
    raw_widths = [
        _TABLE_COLUMN_MIN_WIDTH + (available * flex / flexible_total)
        for flex in flexible
    ]
    fitted = [int(width) for width in raw_widths]
    remainder = target_total - sum(fitted)
    if remainder > 0:
        fractions = sorted(
            (
                (raw_widths[idx] - fitted[idx], idx)
                for idx in range(len(fitted))
            ),
            reverse=True,
        )
        for _fraction, idx in fractions[:remainder]:
            fitted[idx] += 1
    return fitted


def _default_table_column_widths(cols: int) -> list[int]:
    if cols <= 0:
        return []
    if cols == 1:
        return [_TABLE_SINGLE_COLUMN_WIDTH]
    target_total = _table_target_total_width(cols)
    base = target_total // cols
    widths = [base] * cols
    for idx in range(target_total - base * cols):
        widths[idx] += 1
    return widths


def _normalize_column_widths(value: object, cols: int) -> list[int]:
    if not isinstance(value, list) or cols <= 0:
        return []
    widths: list[int] = []
    for item in value:
        width = _safe_int(item)
        if width <= 0:
            return []
        widths.append(width)
    if len(widths) != cols:
        return []
    return widths


def _display_units(text: str) -> int:
    units = 0
    for char in text:
        if unicodedata.east_asian_width(char) in {"F", "W"}:
            units += 2
        else:
            units += 1
    return units


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _get_image_display_size(image_path: Path | None) -> tuple[int, int] | None:
    if image_path is None or not image_path.exists() or not image_path.is_file():
        return None
    size = _read_image_pixel_size(image_path)
    if size is None:
        return None
    width, height = size
    if width <= 0 or height <= 0:
        return None
    display_width = min(width, _IMAGE_DISPLAY_MAX_WIDTH)
    display_height = max(1, round(display_width * height / width))
    return display_width, display_height


def _read_image_pixel_size(image_path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(image_path) as image:
            width, height = image.size
        return int(width), int(height)
    except Exception:
        if image_path.suffix.lower() != ".svg":
            return None
    text = image_path.read_text(encoding="utf-8", errors="ignore")
    width = _parse_svg_length(_match_svg_attr(text, "width"))
    height = _parse_svg_length(_match_svg_attr(text, "height"))
    if width and height:
        return width, height
    view_box = _match_svg_attr(text, "viewBox")
    if not view_box:
        return None
    parts = re.split(r"[\s,]+", view_box.strip())
    if len(parts) != 4:
        return None
    try:
        return round(float(parts[2])), round(float(parts[3]))
    except ValueError:
        return None


def _match_svg_attr(text: str, attr: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(attr)}\s*=\s*['\"](?P<value>[^'\"]+)['\"]",
        text,
        re.IGNORECASE,
    )
    return match.group("value") if match else None


def _parse_svg_length(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"^\s*(?P<number>\d+(?:\.\d+)?)", value)
    if match is None:
        return None
    return round(float(match.group("number")))


def _find_figure_id_for_offset(markdown: str, offset: int) -> str | None:
    last_start: re.Match[str] | None = None
    for match in _FIGURE_START_PATTERN.finditer(markdown):
        if match.start() > offset:
            break
        last_start = match
    if last_start is None:
        return None
    end_match = _FIGURE_END_PATTERN.search(markdown, last_start.end())
    if end_match is not None and offset > end_match.start():
        return None
    return last_start.group("id")


def _extract_figure_id_from_image_ref(ref: str) -> str | None:
    normalized = unquote(ref).split("#", 1)[0].split("?", 1)[0]
    name = Path(normalized.replace("\\", "/")).name
    match = re.search(r"\bfig[-_](?P<id>\d+(?:[-_]\d+)+)", name, re.IGNORECASE)
    if match is None:
        return None
    return match.group("id").replace("_", "-")


def _find_local_figure_asset(
    base_path: str | Path | None,
    figure_id: str | None,
) -> Path | None:
    if base_path is None or not figure_id:
        return None
    base_dir = Path(base_path)
    if base_dir.is_file():
        base_dir = base_dir.parent
    candidate_dirs = [
        base_dir,
        base_dir / "figures",
        base_dir / "插图",
        base_dir / "assets",
    ]
    suffixes = (
        ".drawio.png",
        ".png",
        ".drawio.jpg",
        ".jpg",
        ".jpeg",
        ".drawio.webp",
        ".webp",
        ".drawio.svg",
        ".svg",
    )
    for directory in candidate_dirs:
        for suffix in suffixes:
            candidate = directory / f"fig-{figure_id}{suffix}"
            if candidate.exists() and candidate.is_file():
                return candidate
    return None


def _write_data_image_to_temp(ref: str, *, figure_id: str | None) -> Path | None:
    match = re.match(
        r"^data:(?P<mime>[^;,]+)(?P<encoding>;base64)?,(?P<data>.*)$",
        ref,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    mime = match.group("mime").lower()
    raw_data = match.group("data")
    try:
        if match.group("encoding"):
            payload = base64.b64decode(raw_data, validate=False)
        else:
            payload = unquote(raw_data).encode("utf-8")
    except (binascii.Error, ValueError):
        return None
    if not payload:
        return None
    suffix = _suffix_for_data_mime(mime)
    digest = _hash_text(ref)
    name = f"{figure_id or 'embedded'}-{digest[:12]}{suffix}"
    target_dir = Path(tempfile.gettempdir()) / "larksync-embedded-images"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    if not target.exists():
        target.write_bytes(payload)
    return target


def _suffix_for_data_mime(mime: str) -> str:
    if mime == "image/svg+xml":
        return ".svg"
    if mime == "image/png":
        return ".png"
    if mime == "image/jpeg":
        return ".jpg"
    if mime == "image/webp":
        return ".webp"
    if mime == "image/gif":
        return ".gif"
    return ".bin"
