from __future__ import annotations

import json
from urllib.parse import unquote

from loguru import logger

from src.services.docx_parser import (
    BLOCK_TYPE_SHEET,
    SHEET_PREVIEW_MAX_COLS,
    SHEET_PREVIEW_MAX_ROWS,
)
from src.services.sheet_service import SheetService


class TranscoderSheetHelper:
    def __init__(self, sheet_service: SheetService | None = None) -> None:
        self._sheet_service = sheet_service

    async def prepare_sheet_tables(self, blocks: list[dict]) -> dict[str, list[str]]:
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
            lines = await self.resolve_sheet_markdown_lines(block)
            if not lines:
                continue
            resolved[block_id] = lines
            if token:
                by_token[token] = lines
        return resolved

    async def resolve_sheet_markdown_lines(self, block: dict) -> list[str]:
        if self._sheet_service is None:
            return []
        sheet = block.get("sheet") or {}
        raw_token = str(sheet.get("token") or "").strip()
        if not raw_token:
            return []
        spreadsheet_token, sheet_id = self.split_sheet_token(raw_token)
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
                    matrix[row_index][col_index] = self.sheet_cell_text(row[col_index])

            trimmed = self.trim_sheet_matrix(matrix)
            if not trimmed:
                return []
            return self.build_sheet_markdown_table(trimmed)
        except Exception as exc:
            logger.warning("内嵌 sheet 转码失败: token={} error={}", raw_token, exc)
            return []

    @staticmethod
    def split_sheet_token(raw_token: str) -> tuple[str, str | None]:
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
    def sheet_placeholder_lines(block: dict) -> list[str]:
        sheet = block.get("sheet") or {}
        token = str(sheet.get("token") or "").strip()
        title = str(sheet.get("title") or sheet.get("name") or "内嵌表格").strip()
        if token:
            return [f"{title}（sheet_token: {token}）"]
        return [title]

    @staticmethod
    def build_sheet_markdown_table(matrix: list[list[str]]) -> list[str]:
        if not matrix:
            return []
        cols = max(len(row) for row in matrix)
        if cols <= 0:
            return []
        normalized = [row + [""] * (cols - len(row)) for row in matrix]
        escaped = [
            [TranscoderSheetHelper.escape_markdown_cell(cell) for cell in row]
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
    def trim_sheet_matrix(matrix: list[list[str]]) -> list[list[str]]:
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
    def escape_markdown_cell(value: str) -> str:
        text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("|", "\\|")
        if "\n" in text:
            text = "<br>".join(part.strip() for part in text.split("\n"))
        return text

    @staticmethod
    def sheet_cell_text(value: object, depth: int = 5) -> str:
        if depth < 0:
            return ""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [TranscoderSheetHelper.sheet_cell_text(item, depth - 1) for item in value]
            return "".join(part for part in parts if part)
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                styled = TranscoderSheetHelper.sheet_apply_inline_style(
                    text,
                    value.get("segmentStyle") or value.get("text_element_style"),
                )
                link = TranscoderSheetHelper.sheet_extract_link(value.get("link"), depth - 1)
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
                    candidate = TranscoderSheetHelper.sheet_cell_text(
                        value.get(key),
                        depth - 1,
                    )
                    if candidate:
                        return candidate
            for key in ("elements", "children", "segments", "runs", "richText", "rich_text"):
                nested = value.get(key)
                if isinstance(nested, list):
                    candidate = TranscoderSheetHelper.sheet_cell_text(nested, depth - 1)
                    if candidate:
                        return candidate
            for nested in value.values():
                candidate = TranscoderSheetHelper.sheet_cell_text(nested, depth - 1)
                if candidate:
                    return candidate
        return ""

    @staticmethod
    def sheet_extract_link(value: object, depth: int = 3) -> str | None:
        if depth < 0 or value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return unquote(cleaned) if cleaned else None
        if isinstance(value, dict):
            for key in ("url", "href", "link"):
                nested = value.get(key)
                extracted = TranscoderSheetHelper.sheet_extract_link(nested, depth - 1)
                if extracted:
                    return extracted
        return None

    @staticmethod
    def sheet_apply_inline_style(text: str, style: object) -> str:
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
    def render_add_ons_block(block: dict) -> list[str]:
        add_ons = block.get("add_ons")
        if not isinstance(add_ons, dict):
            return []
        data = TranscoderSheetHelper.extract_add_ons_data(add_ons)
        if not data:
            return []
        payload = data.strip()
        if not payload:
            return []
        if TranscoderSheetHelper.looks_like_mermaid(payload):
            return ["```mermaid", *payload.splitlines(), "```"]
        return ["```text", *payload.splitlines(), "```"]

    @staticmethod
    def extract_add_ons_data(add_ons: dict) -> str:
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
    def looks_like_mermaid(payload: str) -> bool:
        head = payload.lstrip().lower()
        for keyword in ("graph ", "flowchart ", "sequencediagram", "classdiagram"):
            if head.startswith(keyword):
                return True
        return False


__all__ = ["TranscoderSheetHelper"]
