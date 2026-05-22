from __future__ import annotations

from datetime import datetime
from typing import Callable
from urllib.parse import unquote

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
            rendered = f"$$\n{content}\n$$" if "\n" in content else f"${content}$"
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


__all__ = [
    "BLOCK_TYPE_ADD_ONS",
    "BLOCK_TYPE_BULLET",
    "BLOCK_TYPE_CALLOUT",
    "BLOCK_TYPE_CODE",
    "BLOCK_TYPE_DIVIDER",
    "BLOCK_TYPE_FILE",
    "BLOCK_TYPE_GRID",
    "BLOCK_TYPE_GRID_COLUMN",
    "BLOCK_TYPE_HEADING_MAX",
    "BLOCK_TYPE_HEADING_MIN",
    "BLOCK_TYPE_IMAGE",
    "BLOCK_TYPE_ORDERED",
    "BLOCK_TYPE_PAGE",
    "BLOCK_TYPE_QUOTE",
    "BLOCK_TYPE_QUOTE_CONTAINER",
    "BLOCK_TYPE_SHEET",
    "BLOCK_TYPE_TABLE",
    "BLOCK_TYPE_TABLE_CELL",
    "BLOCK_TYPE_TEXT",
    "BLOCK_TYPE_TODO",
    "DocxParser",
    "LIST_BLOCK_TYPES",
    "SHEET_PREVIEW_MAX_COLS",
    "SHEET_PREVIEW_MAX_ROWS",
    "_format_reminder",
    "_normalize_table_cell_text",
    "_resolve_ordered_index",
]
