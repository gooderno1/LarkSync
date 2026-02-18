from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

from loguru import logger

from src.core.paths import data_dir
from src.services.feishu_client import FeishuClient
from src.services.file_downloader import FileDownloader
from src.services.path_sanitizer import sanitize_filename
from src.services.sheet_service import SheetService

BLOCK_TYPE_PAGE = 1
BLOCK_TYPE_TEXT = 2
BLOCK_TYPE_HEADING_MIN = 3
BLOCK_TYPE_HEADING_MAX = 11
BLOCK_TYPE_BULLET = 12
BLOCK_TYPE_ORDERED = 13
BLOCK_TYPE_CODE = 14
BLOCK_TYPE_QUOTE = 15
BLOCK_TYPE_TODO = 17
BLOCK_TYPE_CALLOUT = 19
BLOCK_TYPE_DIVIDER = 22
BLOCK_TYPE_FILE = 23
BLOCK_TYPE_GRID = 24
BLOCK_TYPE_GRID_COLUMN = 25
BLOCK_TYPE_IMAGE = 27
BLOCK_TYPE_SHEET = 30
BLOCK_TYPE_TABLE = 31
BLOCK_TYPE_TABLE_CELL = 32
BLOCK_TYPE_QUOTE_CONTAINER = 34
BLOCK_TYPE_ADD_ONS = 40

LIST_BLOCK_TYPES = {BLOCK_TYPE_BULLET, BLOCK_TYPE_ORDERED, BLOCK_TYPE_TODO}
SHEET_PREVIEW_MAX_ROWS = 30
SHEET_PREVIEW_MAX_COLS = 12

_TEXT_BLOCK_FIELDS = {
    BLOCK_TYPE_TEXT: "text",
    BLOCK_TYPE_BULLET: "bullet",
    BLOCK_TYPE_ORDERED: "ordered",
    BLOCK_TYPE_CODE: "code",
    BLOCK_TYPE_QUOTE: "quote",
    BLOCK_TYPE_TODO: "todo",
}


def _default_assets_root() -> Path:
    return data_dir() / "assets"


class MediaDownloader:
    def __init__(
        self, client: FeishuClient | None = None, base_url: str = "https://open.feishu.cn"
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def download(self, file_token: str, output_path: Path) -> None:
        url = f"{self._base_url}/open-apis/drive/v1/medias/{file_token}/download"
        response = await self._client.request("GET", url)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

    async def close(self) -> None:
        await self._client.close()


class DocxParser:
    def __init__(
        self,
        blocks: list[dict],
        link_rewriter: Callable[[str], str] | None = None,
    ) -> None:
        self._blocks = blocks
        self._link_rewriter = link_rewriter
        self._block_map = {
            block_id: block
            for block in blocks
            if (block_id := block.get("block_id"))
        }
        self._children_map = {
            block_id: [
                child
                for child in (block.get("children") or [])
                if child in self._block_map
            ]
            for block_id, block in self._block_map.items()
        }

    def resolve_order(self) -> list[str]:
        root = self._find_root()
        if root and root.get("block_id"):
            return self.children_ids(root["block_id"])
        top_level: list[str] = []
        for block in self._blocks:
            block_id = block.get("block_id")
            if block_id and not block.get("parent_id"):
                top_level.append(block_id)
        if top_level:
            return top_level
        return [block_id for block_id in self._block_map]

    def _find_root(self) -> dict | None:
        for block in self._blocks:
            if block.get("block_type") == BLOCK_TYPE_PAGE and not block.get("parent_id"):
                return block
        for block in self._blocks:
            if block.get("block_type") == BLOCK_TYPE_PAGE:
                return block
        return None

    def get_block(self, block_id: str) -> dict | None:
        return self._block_map.get(block_id)

    def children_ids(self, block_id: str) -> list[str]:
        return self._children_map.get(block_id, [])

    def text_from_block(self, block: dict, *, strip: bool = True) -> str:
        text_block = self._resolve_text_block(block)
        if not text_block:
            return ""
        elements = text_block.get("elements") or []
        parts: list[str] = []
        for element in elements:
            formatted = self._format_element(element)
            if formatted:
                parts.append(formatted)
        text = "".join(parts)
        return text.strip() if strip else text

    def collect_text(self, block_id: str, max_depth: int = 6) -> str:
        block = self.get_block(block_id)
        if not block or max_depth < 0:
            return ""
        parts: list[str] = []
        text = self.text_from_block(block)
        if text:
            parts.append(text)
        for child_id in self.children_ids(block_id):
            child_text = self.collect_text(child_id, max_depth=max_depth - 1)
            if child_text:
                parts.append(child_text)
        return " ".join(parts).strip()

    def _resolve_text_block(self, block: dict) -> dict | None:
        block_type = block.get("block_type")
        heading_field = self._heading_field(block_type)
        if heading_field and heading_field in block:
            return self._extract_text_container(block.get(heading_field))
        field = _TEXT_BLOCK_FIELDS.get(block_type)
        if field and field in block:
            container = self._extract_text_container(block.get(field))
            if container:
                return container
        if "text" in block:
            container = self._extract_text_container(block.get("text"))
            if container:
                return container
        return self._find_text_container(block, max_depth=3)

    def _heading_field(self, block_type: int | None) -> str | None:
        if not block_type:
            return None
        if BLOCK_TYPE_HEADING_MIN <= block_type <= BLOCK_TYPE_HEADING_MAX:
            return f"heading{block_type - 2}"
        return None

    @classmethod
    def _find_text_container(cls, value: object, max_depth: int) -> dict | None:
        if max_depth < 0:
            return None
        if isinstance(value, dict):
            direct = cls._extract_text_container(value)
            if direct:
                return direct
            for nested in value.values():
                found = cls._find_text_container(nested, max_depth - 1)
                if found:
                    return found
            return None
        if isinstance(value, list):
            for item in value:
                found = cls._find_text_container(item, max_depth - 1)
                if found:
                    return found
        return None

    @staticmethod
    def _extract_text_container(value: object) -> dict | None:
        if not isinstance(value, dict):
            return None
        if isinstance(value.get("elements"), list):
            return value
        for key in ("text", "content", "title"):
            nested = value.get(key)
            if isinstance(nested, dict) and isinstance(nested.get("elements"), list):
                return nested
        return None

    def _format_text_run(self, text_run: dict) -> str:
        content = text_run.get("content") or ""
        if not content:
            return ""
        style = text_run.get("text_element_style") or {}
        text = self._apply_text_style(content, style)
        link = style.get("link") or {}
        if link.get("url"):
            url = unquote(link.get("url"))
            if self._link_rewriter:
                url = self._link_rewriter(url)
            text = f"[{text}]({url})"
        return text

    def _format_element(self, element: dict) -> str:
        text_run = element.get("text_run")
        if text_run:
            return self._format_text_run(text_run)
        mention_doc = element.get("mention_doc")
        if mention_doc:
            title = mention_doc.get("title") or mention_doc.get("token") or "文档"
            style = mention_doc.get("text_element_style") or {}
            text = self._apply_text_style(title, style)
            url = mention_doc.get("url")
            if url:
                if self._link_rewriter:
                    url = self._link_rewriter(url)
                return f"[{text}]({url})"
            return text
        mention_user = element.get("mention_user")
        if mention_user:
            user_id = mention_user.get("user_id") or "unknown"
            style = mention_user.get("text_element_style") or {}
            return self._apply_text_style(f"@{user_id}", style)
        reminder = element.get("reminder")
        if reminder:
            style = reminder.get("text_element_style") or {}
            text = _format_reminder(reminder)
            return self._apply_text_style(text, style)
        equation = element.get("equation")
        if equation:
            if not isinstance(equation, dict):
                return ""
            content = str(equation.get("content") or "").strip()
            if not content:
                return ""
            style = equation.get("text_element_style") or {}
            rendered = (
                f"$$\n{content}\n$$"
                if "\n" in content
                else f"${content}$"
            )
            return self._apply_text_style(rendered, style)
        generic = self._fallback_element_text(element)
        if generic:
            return generic
        if element.get("line_break") is not None or element.get("linebreak") is not None:
            return "\n"
        if element.get("hard_break") is not None:
            return "\n"
        return ""

    @staticmethod
    def _apply_text_style(text: str, style: dict) -> str:
        if style.get("inline_code"):
            text = f"`{text}`"
        if style.get("bold"):
            text = f"**{text}**"
        if style.get("italic"):
            text = f"*{text}*"
        if style.get("strikethrough"):
            text = f"~~{text}~~"
        if style.get("underline"):
            text = f"<u>{text}</u>"
        return text

    @classmethod
    def _fallback_element_text(cls, value: object, depth: int = 3) -> str:
        if depth < 0:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [cls._fallback_element_text(item, depth - 1) for item in value]
            return "".join(part for part in parts if part)
        if not isinstance(value, dict):
            return ""

        text = value.get("text")
        link = value.get("link")
        if isinstance(text, str) and text:
            if isinstance(link, str) and link:
                return f"[{text}]({link})"
            return text

        for key in ("content", "value", "name", "title"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate

        for key in ("elements", "children", "segments"):
            nested = value.get(key)
            if isinstance(nested, list):
                parsed = cls._fallback_element_text(nested, depth - 1)
                if parsed:
                    return parsed

        nested_parts: list[str] = []
        for nested in value.values():
            parsed = cls._fallback_element_text(nested, depth - 1)
            if parsed:
                nested_parts.append(parsed)
        return "".join(nested_parts)

    def table_markdown(self, block: dict) -> str:
        table = block.get("table") or {}
        raw_cells = table.get("cells") or []
        cells = self._flatten_table_cells(raw_cells)
        if not cells:
            cells = block.get("children") or []
        prop = table.get("property") or {}
        rows = int(prop.get("row_size") or 0)
        cols = int(prop.get("column_size") or 0)
        if rows <= 0 or cols <= 0:
            return ""

        matrix = [["" for _ in range(cols)] for _ in range(rows)]
        for idx, cell_id in enumerate(cells):
            row_index = idx // cols
            col_index = idx % cols
            if row_index >= rows:
                continue
            matrix[row_index][col_index] = self._table_cell_text(cell_id)

        header = "| " + " | ".join(matrix[0]) + " |"
        separator = "| " + " | ".join(["---"] * cols) + " |"
        body = [
            "| " + " | ".join(row) + " |" for row in matrix[1:] if row is not None
        ]
        return "\n".join([header, separator, *body])

    @staticmethod
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

    def _table_cell_text(self, cell_id: str) -> str:
        cell = self.get_block(cell_id)
        if not cell:
            return ""
        children = cell.get("children") or []
        if not children:
            return _normalize_table_cell_text(self.collect_text(cell_id))
        parts: list[str] = []
        for child_id in children:
            text = self.collect_text(child_id)
            if text:
                parts.append(text)
        return _normalize_table_cell_text("<br>".join(parts).strip())


class _LineBuffer:
    def __init__(self, blank_line: str = "") -> None:
        self.lines: list[str] = []
        self._blank_line = blank_line

    def add_block(self, block_lines: list[str]) -> None:
        if not block_lines:
            return
        if self.lines and self.lines[-1] != self._blank_line:
            self.lines.append(self._blank_line)
        self.lines.extend(block_lines)


class DocxTranscoder:
    def __init__(
        self,
        assets_root: Path | None = None,
        downloader: MediaDownloader | None = None,
        file_downloader: FileDownloader | None = None,
        sheet_service: SheetService | None = None,
        attachments_dir_name: str = "attachments",
    ) -> None:
        self._assets_root = assets_root or _default_assets_root()
        self._assets_relative = Path("assets")
        self._downloader = downloader or MediaDownloader()
        self._file_downloader = file_downloader or FileDownloader()
        self._sheet_service = sheet_service
        self._attachments_dir_name = attachments_dir_name

    async def to_markdown(
        self,
        document_id: str,
        blocks: list[dict],
        *,
        base_dir: Path | None = None,
        link_map: dict[str, Path] | None = None,
    ) -> str:
        resolved_base = Path(base_dir) if base_dir is not None else None
        resolved_link_map = link_map or {}
        link_rewriter = self._build_link_rewriter(resolved_base, resolved_link_map)

        parser = DocxParser(blocks, link_rewriter=link_rewriter)
        ordered_ids = parser.resolve_order()
        sheet_tables = await self._prepare_sheet_tables(blocks)
        images: list[tuple[str, Path]] = []
        attachments: list[tuple[str, str, Path]] = []
        lines = self._render_block_ids(
            ordered_ids,
            parser,
            document_id,
            images,
            attachments,
            base_dir=resolved_base,
            link_map=resolved_link_map,
            base_indent="",
            quote_prefix="",
            sheet_tables=sheet_tables,
        )

        for token, path in images:
            try:
                await self._downloader.download(token, path)
            except Exception:
                try:
                    await self._file_downloader.download(
                        file_token=token,
                        file_name=path.name,
                        target_dir=path.parent,
                        mtime=time.time(),
                    )
                except Exception:
                    continue

        for token, name, target_dir in attachments:
            try:
                await self._file_downloader.download(
                    file_token=token,
                    file_name=name,
                    target_dir=target_dir,
                    mtime=time.time(),
                )
            except Exception:
                try:
                    output_path = target_dir / name
                    await self._downloader.download(token, output_path)
                except Exception:
                    continue

        return "\n".join(lines).strip()

    def _render_block_ids(
        self,
        block_ids: list[str],
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        base_indent: str,
        quote_prefix: str,
        sheet_tables: dict[str, list[str]],
    ) -> list[str]:
        blank_line = quote_prefix.rstrip() if quote_prefix else ""
        buffer = _LineBuffer(blank_line=blank_line)
        index = 0
        while index < len(block_ids):
            block_id = block_ids[index]
            block = parser.get_block(block_id)
            if not block:
                index += 1
                continue
            block_type = block.get("block_type")
            if block_type in LIST_BLOCK_TYPES:
                group_ids = [block_id]
                list_type = block_type
                index += 1
                while index < len(block_ids):
                    next_block = parser.get_block(block_ids[index])
                    if next_block and next_block.get("block_type") == list_type:
                        group_ids.append(block_ids[index])
                        index += 1
                    else:
                        break
                lines = self._render_list_group(
                    group_ids,
                    list_type,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
                buffer.add_block(lines)
                continue

            lines = self._render_block(
                block,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                base_indent=base_indent,
                quote_prefix=quote_prefix,
                sheet_tables=sheet_tables,
            )
            buffer.add_block(lines)
            index += 1

        return buffer.lines

    def _render_list_group(
        self,
        block_ids: list[str],
        list_type: int,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        base_indent: str,
        quote_prefix: str,
        sheet_tables: dict[str, list[str]],
    ) -> list[str]:
        marker = "- "
        if list_type == BLOCK_TYPE_ORDERED:
            marker = ""
        elif list_type == BLOCK_TYPE_TODO:
            marker = "- [ ] "

        prefix = f"{quote_prefix}{base_indent}"
        keep_blank = bool(quote_prefix)
        lines: list[str] = []
        ordered_index: int | None = None
        for block_id in block_ids:
            block = parser.get_block(block_id)
            if not block:
                continue
            text = parser.text_from_block(block, strip=False)
            effective_marker = marker
            if list_type == BLOCK_TYPE_TODO:
                todo = block.get("todo") or {}
                style = todo.get("style") or {}
                if style.get("done"):
                    effective_marker = "- [x] "
            elif list_type == BLOCK_TYPE_ORDERED:
                ordered = block.get("ordered") or {}
                style = ordered.get("style") or {}
                sequence = style.get("sequence")
                ordered_index = _resolve_ordered_index(ordered_index, sequence)
                effective_marker = f"{ordered_index}. "
            text_lines = self._split_multiline_text(text)
            first_line = f"{effective_marker}{text_lines[0]}".rstrip()
            lines.append(self._line_with_prefix(prefix, first_line, keep_blank=keep_blank))
            continuation_prefix = f"{prefix}{' ' * len(effective_marker)}"
            for continuation in text_lines[1:]:
                lines.append(
                    self._line_with_prefix(
                        continuation_prefix, continuation, keep_blank=keep_blank
                    )
                )
            children = parser.children_ids(block_id)
            if children:
                indent_step = "   " if list_type == BLOCK_TYPE_ORDERED else "  "
                child_lines = self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=f"{base_indent}{indent_step}",
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
                lines.extend(child_lines)
        return lines

    def _render_block(
        self,
        block: dict,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        base_indent: str,
        quote_prefix: str,
        sheet_tables: dict[str, list[str]],
    ) -> list[str]:
        block_type = block.get("block_type")
        prefix = f"{quote_prefix}{base_indent}"
        keep_blank = bool(quote_prefix)

        if block_type == BLOCK_TYPE_PAGE:
            children = parser.children_ids(block.get("block_id", ""))
            if children:
                return self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
            return []

        if block_type == BLOCK_TYPE_TABLE_CELL:
            return []

        if BLOCK_TYPE_HEADING_MIN <= (block_type or 0) <= BLOCK_TYPE_HEADING_MAX:
            level = block_type - 2
            text = parser.text_from_block(block)
            if not text:
                return []
            line = f"{'#' * level} {text}".strip()
            lines = [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]
            children = parser.children_ids(block.get("block_id", ""))
            if children:
                child_lines = self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
                if lines and child_lines and lines[-1] != "":
                    lines.append("")
                lines.extend(child_lines)
            return lines

        if block_type == BLOCK_TYPE_TEXT:
            text = parser.text_from_block(block, strip=False)
            lines: list[str] = []
            if text:
                lines.extend(
                    self._prefix_lines(
                        prefix,
                        self._split_multiline_text(text),
                        keep_blank=keep_blank,
                    )
                )
            children = parser.children_ids(block.get("block_id", ""))
            if children:
                child_lines = self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
                if lines and child_lines and lines[-1] != "":
                    lines.append("")
                lines.extend(child_lines)
            return lines

        if block_type == BLOCK_TYPE_CODE:
            text = parser.text_from_block(block, strip=False)
            code_block = block.get("code") or {}
            language = code_block.get("language")
            fence = "```"
            if isinstance(language, str) and language.strip():
                fence = f"```{language.strip()}"
            raw_lines = [fence]
            raw_lines.extend(text.splitlines() or [""])
            raw_lines.append("```")
            return self._prefix_lines(prefix, raw_lines, keep_blank=keep_blank)

        if block_type == BLOCK_TYPE_SHEET:
            block_id = str(block.get("block_id") or "")
            sheet_lines = sheet_tables.get(block_id) or self._sheet_placeholder_lines(block)
            return self._prefix_lines(prefix, sheet_lines, keep_blank=keep_blank)

        if block_type == BLOCK_TYPE_ADD_ONS:
            addon_lines = self._render_add_ons_block(block)
            if not addon_lines:
                return []
            return self._prefix_lines(prefix, addon_lines, keep_blank=keep_blank)

        if block_type == BLOCK_TYPE_TABLE:
            table_lines = self._render_table(
                block,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                sheet_tables=sheet_tables,
            )
            if not table_lines:
                return []
            return self._prefix_lines(prefix, table_lines, keep_blank=keep_blank)

        if block_type == BLOCK_TYPE_IMAGE:
            image = block.get("image") or {}
            token = image.get("token")
            if not token:
                return []
            filename = f"{token}.png"
            if base_dir:
                output_path = base_dir / self._assets_relative / document_id / filename
            else:
                output_path = self._assets_root / document_id / filename
            relative_path = self._assets_relative / document_id / filename
            images.append((token, output_path))
            line = f"![]({relative_path.as_posix()})"
            return [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]

        if block_type == BLOCK_TYPE_FILE:
            token, name = self._extract_file_info(block)
            if not token or not name:
                return []
            safe_name = sanitize_filename(name)
            if base_dir and token in link_map:
                rel_link = self._relative_link(base_dir, link_map[token])
                line = f"[{name}]({rel_link})"
                return [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]
            if not base_dir:
                return [self._line_with_prefix(prefix, name, keep_blank=keep_blank)]
            attachments_dir = base_dir / self._attachments_dir_name
            attachments.append((token, safe_name, attachments_dir))
            rel = Path(self._attachments_dir_name) / safe_name
            line = f"[{name}]({rel.as_posix()})"
            return [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]

        if block_type == BLOCK_TYPE_DIVIDER:
            return [self._line_with_prefix(prefix, "---", keep_blank=keep_blank)]

        if block_type in (BLOCK_TYPE_QUOTE, BLOCK_TYPE_CALLOUT, BLOCK_TYPE_QUOTE_CONTAINER):
            return self._render_quote_container(
                block,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                base_indent=base_indent,
                quote_prefix=quote_prefix,
                sheet_tables=sheet_tables,
            )

        if block_type in (BLOCK_TYPE_GRID, BLOCK_TYPE_GRID_COLUMN):
            children = parser.children_ids(block.get("block_id", ""))
            if children:
                return self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    attachments,
                    base_dir=base_dir,
                    link_map=link_map,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                    sheet_tables=sheet_tables,
                )
            return []

        children = parser.children_ids(block.get("block_id", ""))
        if children:
            return self._render_block_ids(
                children,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                base_indent=base_indent,
                quote_prefix=quote_prefix,
                sheet_tables=sheet_tables,
            )

        fallback_text = parser.text_from_block(block, strip=False)
        if fallback_text:
            return self._prefix_lines(
                prefix,
                self._split_multiline_text(fallback_text),
                keep_blank=keep_blank,
            )

        return []

    def _render_quote_container(
        self,
        block: dict,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        base_indent: str,
        quote_prefix: str,
        sheet_tables: dict[str, list[str]],
    ) -> list[str]:
        new_quote_prefix = f"{quote_prefix}> "
        blank_line = new_quote_prefix.rstrip()
        buffer = _LineBuffer(blank_line=blank_line)

        text = parser.text_from_block(block)
        if text:
            prefix = f"{new_quote_prefix}{base_indent}"
            buffer.add_block([self._line_with_prefix(prefix, text, keep_blank=True)])

        children = parser.children_ids(block.get("block_id", ""))
        if children:
            child_lines = self._render_block_ids(
                children,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                base_indent=base_indent,
                quote_prefix=new_quote_prefix,
                sheet_tables=sheet_tables,
            )
            buffer.add_block(child_lines)

        return buffer.lines

    def _render_table(
        self,
        block: dict,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        sheet_tables: dict[str, list[str]],
    ) -> list[str]:
        table = block.get("table") or {}
        raw_cells = table.get("cells") or []
        cells = self._flatten_table_cells(raw_cells)
        if not cells:
            cells = block.get("children") or []
        prop = table.get("property") or {}
        rows = int(prop.get("row_size") or 0)
        cols = int(prop.get("column_size") or 0)
        if rows <= 0 or cols <= 0:
            return []

        matrix = [["" for _ in range(cols)] for _ in range(rows)]
        for idx, cell_id in enumerate(cells):
            row_index = idx // cols
            col_index = idx % cols
            if row_index >= rows:
                continue
            matrix[row_index][col_index] = self._render_table_cell(
                cell_id,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                sheet_tables=sheet_tables,
            )

        header = "| " + " | ".join(matrix[0]) + " |"
        separator = "| " + " | ".join(["---"] * cols) + " |"
        body = ["| " + " | ".join(row) + " |" for row in matrix[1:]]
        return [header, separator, *body]

    def _render_table_cell(
        self,
        cell_id: str,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        attachments: list[tuple[str, str, Path]],
        *,
        base_dir: Path | None,
        link_map: dict[str, Path],
        sheet_tables: dict[str, list[str]],
    ) -> str:
        cell = parser.get_block(cell_id)
        if not cell:
            return ""
        children = cell.get("children") or []
        if children:
            lines = self._render_block_ids(
                children,
                parser,
                document_id,
                images,
                attachments,
                base_dir=base_dir,
                link_map=link_map,
                base_indent="",
                quote_prefix="",
                sheet_tables=sheet_tables,
            )
            visible = [line for line in lines if line != ""]
            if not visible:
                return ""
            formatted = [self._format_table_cell_line(line) for line in visible]
            return "<br>".join(formatted)
        text = parser.collect_text(cell_id)
        return _normalize_table_cell_text(text)

    async def _prepare_sheet_tables(
        self,
        blocks: list[dict],
    ) -> dict[str, list[str]]:
        if self._sheet_service is None:
            return {}
        resolved: dict[str, list[str]] = {}
        by_token: dict[str, list[str]] = {}
        for block in blocks:
            if block.get("block_type") != BLOCK_TYPE_SHEET:
                continue
            block_id = str(block.get("block_id") or "").strip()
            if not block_id:
                continue
            sheet = block.get("sheet") or {}
            token = str(sheet.get("token") or "").strip()
            if token and token in by_token:
                resolved[block_id] = list(by_token[token])
                continue
            lines = await self._resolve_sheet_markdown_lines(block)
            if not lines:
                continue
            resolved[block_id] = lines
            if token:
                by_token[token] = lines
        return resolved

    async def _resolve_sheet_markdown_lines(self, block: dict) -> list[str]:
        if self._sheet_service is None:
            return []
        sheet = block.get("sheet") or {}
        raw_token = str(sheet.get("token") or "").strip()
        if not raw_token:
            return []
        spreadsheet_token, sheet_id = self._split_sheet_token(raw_token)
        if not spreadsheet_token:
            return []
        try:
            resolved_sheet_id = sheet_id
            if not resolved_sheet_id:
                sheet_ids = await self._sheet_service.list_sheet_ids(spreadsheet_token)
                if sheet_ids:
                    resolved_sheet_id = sheet_ids[0]
            if not resolved_sheet_id:
                return []

            meta = await self._sheet_service.get_sheet_meta(
                spreadsheet_token,
                resolved_sheet_id,
            )
            row_count = max(1, min(meta.row_count, SHEET_PREVIEW_MAX_ROWS))
            column_count = max(1, min(meta.column_count, SHEET_PREVIEW_MAX_COLS))
            raw_values = await self._sheet_service.get_values(
                spreadsheet_token,
                resolved_sheet_id,
                row_count=row_count,
                column_count=column_count,
            )
            matrix = [["" for _ in range(column_count)] for _ in range(row_count)]
            for row_index in range(min(len(raw_values), row_count)):
                row = raw_values[row_index]
                if not isinstance(row, list):
                    continue
                for col_index in range(min(len(row), column_count)):
                    matrix[row_index][col_index] = self._sheet_cell_text(row[col_index])

            trimmed = self._trim_sheet_matrix(matrix)
            if not trimmed:
                return []
            return self._build_sheet_markdown_table(trimmed)
        except Exception as exc:
            logger.warning("内嵌 sheet 转码失败: token={} error={}", raw_token, exc)
            return []

    @staticmethod
    def _split_sheet_token(raw_token: str) -> tuple[str, str | None]:
        token = raw_token.strip()
        if not token:
            return "", None
        if "_" not in token:
            return token, None
        prefix, suffix = token.rsplit("_", 1)
        if prefix and suffix:
            return prefix, suffix
        return token, None

    @staticmethod
    def _sheet_placeholder_lines(block: dict) -> list[str]:
        sheet = block.get("sheet") or {}
        token = str(sheet.get("token") or "").strip()
        title = str(sheet.get("title") or sheet.get("name") or "内嵌表格").strip()
        if token:
            return [f"{title}（sheet_token: {token}）"]
        return [title]

    @staticmethod
    def _build_sheet_markdown_table(matrix: list[list[str]]) -> list[str]:
        if not matrix:
            return []
        cols = max(len(row) for row in matrix)
        if cols <= 0:
            return []
        normalized = [row + [""] * (cols - len(row)) for row in matrix]
        escaped = [
            [DocxTranscoder._escape_markdown_cell(cell) for cell in row]
            for row in normalized
        ]
        header = escaped[0]
        separator = ["---"] * cols
        body = escaped[1:]
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in body)
        return lines

    @staticmethod
    def _trim_sheet_matrix(matrix: list[list[str]]) -> list[list[str]]:
        if not matrix:
            return []
        max_col = 0
        for row in matrix:
            for idx, cell in enumerate(row):
                if str(cell).strip():
                    max_col = max(max_col, idx + 1)
        if max_col == 0:
            return []
        trimmed = [row[:max_col] for row in matrix]
        while trimmed and all(not str(cell).strip() for cell in trimmed[-1]):
            trimmed.pop()
        return trimmed

    @staticmethod
    def _escape_markdown_cell(value: str) -> str:
        text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("|", "\\|")
        if "\n" in text:
            text = "<br>".join(part.strip() for part in text.split("\n"))
        return text

    @staticmethod
    def _sheet_cell_text(value: object, depth: int = 5) -> str:
        if depth < 0:
            return ""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [DocxTranscoder._sheet_cell_text(item, depth - 1) for item in value]
            return "".join(part for part in parts if part)
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                styled = DocxTranscoder._sheet_apply_inline_style(
                    text,
                    value.get("segmentStyle") or value.get("text_element_style"),
                )
                link = DocxTranscoder._sheet_extract_link(value.get("link"), depth - 1)
                if link and styled:
                    return f"[{styled}]({link})"
                if styled:
                    return styled
            for key in (
                "displayValue",
                "formattedValue",
                "display_value",
                "formatted_value",
                "value",
                "content",
                "name",
                "display",
                "label",
                "title",
                "formula",
                "error",
                "errorValue",
                "error_value",
            ):
                if key in value:
                    candidate = DocxTranscoder._sheet_cell_text(value.get(key), depth - 1)
                    if candidate:
                        return candidate
            for key in ("elements", "children", "segments", "runs", "richText", "rich_text"):
                nested = value.get(key)
                if isinstance(nested, list):
                    candidate = DocxTranscoder._sheet_cell_text(nested, depth - 1)
                    if candidate:
                        return candidate
            for nested in value.values():
                candidate = DocxTranscoder._sheet_cell_text(nested, depth - 1)
                if candidate:
                    return candidate
        return ""

    @staticmethod
    def _sheet_extract_link(value: object, depth: int = 3) -> str | None:
        if depth < 0 or value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return unquote(cleaned) if cleaned else None
        if isinstance(value, dict):
            for key in ("url", "href", "link"):
                nested = value.get(key)
                extracted = DocxTranscoder._sheet_extract_link(nested, depth - 1)
                if extracted:
                    return extracted
        return None

    @staticmethod
    def _sheet_apply_inline_style(text: str, style: object) -> str:
        if not isinstance(style, dict):
            return text
        rendered = text
        if style.get("inline_code") or style.get("inlineCode"):
            rendered = f"`{rendered}`"
        if style.get("bold"):
            rendered = f"**{rendered}**"
        if style.get("italic"):
            rendered = f"*{rendered}*"
        if style.get("strikethrough") or style.get("strikeThrough"):
            rendered = f"~~{rendered}~~"
        if style.get("underline"):
            rendered = f"<u>{rendered}</u>"
        return rendered

    @staticmethod
    def _render_add_ons_block(block: dict) -> list[str]:
        add_ons = block.get("add_ons")
        if not isinstance(add_ons, dict):
            return []
        data = DocxTranscoder._extract_add_ons_data(add_ons)
        if not data:
            return []
        payload = data.strip()
        if not payload:
            return []
        if DocxTranscoder._looks_like_mermaid(payload):
            return ["```mermaid", *payload.splitlines(), "```"]
        return ["```text", *payload.splitlines(), "```"]

    @staticmethod
    def _extract_add_ons_data(add_ons: dict) -> str:
        record = add_ons.get("record")
        parsed: object = record
        if isinstance(record, str):
            raw = record.strip()
            if not raw:
                return ""
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return raw
        if isinstance(parsed, dict):
            data = parsed.get("data")
            if isinstance(data, str):
                return data
            try:
                return json.dumps(parsed, ensure_ascii=False)
            except TypeError:
                return ""
        return ""

    @staticmethod
    def _looks_like_mermaid(payload: str) -> bool:
        head = payload.lstrip().lower()
        for keyword in ("graph ", "flowchart ", "sequenceDiagram".lower(), "classDiagram".lower()):
            if head.startswith(keyword):
                return True
        return False

    @staticmethod
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

    @staticmethod
    def _format_table_cell_line(line: str) -> str:
        if not line:
            return ""
        stripped = line.lstrip(" ")
        if stripped == line:
            return line
        leading = len(line) - len(stripped)
        return f"{'&nbsp;' * leading}{stripped}"

    def _build_link_rewriter(
        self, base_dir: Path | None, link_map: dict[str, Path]
    ) -> Callable[[str], str] | None:
        if base_dir is None or not link_map:
            return None
        tokens = sorted(link_map.keys(), key=len, reverse=True)

        def _rewrite(url: str) -> str:
            for token in tokens:
                if token in url:
                    return self._relative_link(base_dir, link_map[token])
            return url

        return _rewrite

    @staticmethod
    def _relative_link(base_dir: Path, target: Path) -> str:
        try:
            rel = os.path.relpath(target, start=base_dir)
            return Path(rel).as_posix()
        except ValueError:
            return target.as_posix()

    @staticmethod
    def _extract_file_info(block: dict) -> tuple[str | None, str | None]:
        file_info = block.get("file")
        if isinstance(file_info, dict):
            token = file_info.get("token") or file_info.get("file_token")
            name = (
                file_info.get("name")
                or file_info.get("title")
                or file_info.get("file_name")
            )
            if not name and token:
                ext = file_info.get("file_extension") or file_info.get("extension")
                name = f"{token}.{ext}" if ext else str(token)
            if token:
                token = str(token)
            if name:
                name = str(name)
            return token, name

        for value in block.values():
            if not isinstance(value, dict):
                continue
            token = value.get("token") or value.get("file_token")
            name = value.get("name") or value.get("title") or value.get("file_name")
            if not name and token:
                ext = value.get("file_extension") or value.get("extension")
                name = f"{token}.{ext}" if ext else str(token)
            if token and name:
                return str(token), str(name)

        return None, None

    @staticmethod
    def _line_with_prefix(prefix: str, content: str, *, keep_blank: bool) -> str:
        if content:
            return f"{prefix}{content}"
        if keep_blank and prefix:
            return prefix.rstrip()
        return ""

    @staticmethod
    def _prefix_lines(prefix: str, lines: list[str], *, keep_blank: bool) -> list[str]:
        if not prefix:
            return lines
        blank_value = prefix.rstrip() if keep_blank else ""
        return [prefix + line if line else blank_value for line in lines]

    @staticmethod
    def _split_multiline_text(text: str) -> list[str]:
        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\u2028", "\n")
            .replace("\u2029", "\n")
            .replace("\u000b", "\n")
        )
        lines = [line.rstrip() for line in normalized.split("\n")]
        return lines if lines else [""]

    async def close(self) -> None:
        close = getattr(self._downloader, "close", None)
        if close:
            await close()
        file_close = getattr(self._file_downloader, "close", None)
        if file_close:
            await file_close()
        sheet_close = getattr(self._sheet_service, "close", None)
        if sheet_close:
            await sheet_close()


def _format_reminder(reminder: dict) -> str:
    timestamp = reminder.get("notify_time") or reminder.get("expire_time")
    if timestamp is None:
        return "提醒"
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return "提醒"
    if ts > 1e12:
        ts = ts // 1000
    try:
        dt = datetime.fromtimestamp(ts)
    except (OSError, ValueError):
        return "提醒"
    return f"提醒({dt:%Y-%m-%d %H:%M})"


def _normalize_table_cell_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in normalized:
        normalized = "<br>".join(normalized.split("\n"))
    return normalized


def _resolve_ordered_index(current: int | None, sequence: object) -> int:
    if isinstance(sequence, str):
        value = sequence.strip().lower()
        if value == "auto":
            return 1 if current is None else current + 1
        if value.isdigit():
            return max(1, int(value))
    if current is None:
        return 1
    return current + 1


__all__ = ["DocxParser", "DocxTranscoder", "MediaDownloader"]
