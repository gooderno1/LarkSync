from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from src.services.feishu_client import FeishuClient

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
BLOCK_TYPE_TABLE = 31
BLOCK_TYPE_TABLE_CELL = 32
BLOCK_TYPE_QUOTE_CONTAINER = 34

LIST_BLOCK_TYPES = {BLOCK_TYPE_BULLET, BLOCK_TYPE_ORDERED, BLOCK_TYPE_TODO}

_TEXT_BLOCK_FIELDS = {
    BLOCK_TYPE_TEXT: "text",
    BLOCK_TYPE_BULLET: "bullet",
    BLOCK_TYPE_ORDERED: "ordered",
    BLOCK_TYPE_CODE: "code",
    BLOCK_TYPE_QUOTE: "quote",
    BLOCK_TYPE_TODO: "todo",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_assets_root() -> Path:
    return _repo_root() / "data" / "assets"


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
    def __init__(self, blocks: list[dict]) -> None:
        self._blocks = blocks
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
            text_run = element.get("text_run")
            if not text_run:
                continue
            parts.append(self._format_text_run(text_run))
        text = "".join(parts)
        return text.strip() if strip else text

    def _resolve_text_block(self, block: dict) -> dict | None:
        block_type = block.get("block_type")
        heading_field = self._heading_field(block_type)
        if heading_field and heading_field in block:
            return block.get(heading_field)
        field = _TEXT_BLOCK_FIELDS.get(block_type)
        if field and field in block:
            return block.get(field)
        if "text" in block:
            return block.get("text")
        for value in block.values():
            if isinstance(value, dict) and isinstance(value.get("elements"), list):
                return value
        return None

    def _heading_field(self, block_type: int | None) -> str | None:
        if not block_type:
            return None
        if BLOCK_TYPE_HEADING_MIN <= block_type <= BLOCK_TYPE_HEADING_MAX:
            return f"heading{block_type - 2}"
        return None

    def _format_text_run(self, text_run: dict) -> str:
        content = text_run.get("content") or ""
        style = text_run.get("text_element_style") or {}

        text = content
        if style.get("bold"):
            text = f"**{text}**"
        if style.get("italic"):
            text = f"*{text}*"
        if style.get("inline_code"):
            text = f"`{text}`"
        link = style.get("link") or {}
        if link.get("url"):
            url = unquote(link.get("url"))
            text = f"[{text}]({url})"
        return text

    def table_markdown(self, block: dict) -> str:
        table = block.get("table") or {}
        cells: list[str] = table.get("cells") or []
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

    def _table_cell_text(self, cell_id: str) -> str:
        cell = self.get_block(cell_id)
        if not cell:
            return ""
        parts: list[str] = []
        for child_id in cell.get("children") or []:
            child = self.get_block(child_id)
            if not child:
                continue
            text = self.text_from_block(child)
            if text:
                parts.append(text)
        return " ".join(parts).strip()


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
    ) -> None:
        self._assets_root = assets_root or _default_assets_root()
        self._assets_relative = Path("assets")
        self._downloader = downloader or MediaDownloader()

    async def to_markdown(self, document_id: str, blocks: list[dict]) -> str:
        parser = DocxParser(blocks)
        ordered_ids = parser.resolve_order()
        images: list[tuple[str, Path]] = []
        lines = self._render_block_ids(
            ordered_ids,
            parser,
            document_id,
            images,
            base_indent="",
            quote_prefix="",
        )

        for token, path in images:
            await self._downloader.download(token, path)

        return "\n".join(lines).strip()

    def _render_block_ids(
        self,
        block_ids: list[str],
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        *,
        base_indent: str,
        quote_prefix: str,
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
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                )
                buffer.add_block(lines)
                continue

            lines = self._render_block(
                block,
                parser,
                document_id,
                images,
                base_indent=base_indent,
                quote_prefix=quote_prefix,
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
        *,
        base_indent: str,
        quote_prefix: str,
    ) -> list[str]:
        marker = "- "
        if list_type == BLOCK_TYPE_ORDERED:
            marker = "1. "
        elif list_type == BLOCK_TYPE_TODO:
            marker = "- [ ] "

        prefix = f"{quote_prefix}{base_indent}"
        keep_blank = bool(quote_prefix)
        lines: list[str] = []
        for block_id in block_ids:
            block = parser.get_block(block_id)
            if not block:
                continue
            text = parser.text_from_block(block)
            line = f"{marker}{text}".rstrip()
            lines.append(self._line_with_prefix(prefix, line, keep_blank=keep_blank))
            children = parser.children_ids(block_id)
            if children:
                child_lines = self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    base_indent=f"{base_indent}  ",
                    quote_prefix=quote_prefix,
                )
                lines.extend(child_lines)
        return lines

    def _render_block(
        self,
        block: dict,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        *,
        base_indent: str,
        quote_prefix: str,
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
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
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
            return [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]

        if block_type == BLOCK_TYPE_TEXT:
            text = parser.text_from_block(block)
            if not text:
                return []
            return [self._line_with_prefix(prefix, text, keep_blank=keep_blank)]

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

        if block_type == BLOCK_TYPE_TABLE:
            table_md = parser.table_markdown(block)
            if not table_md:
                return []
            return self._prefix_lines(prefix, table_md.splitlines(), keep_blank=keep_blank)

        if block_type == BLOCK_TYPE_IMAGE:
            image = block.get("image") or {}
            token = image.get("token")
            if not token:
                return []
            filename = f"{token}.png"
            output_path = self._assets_root / document_id / filename
            relative_path = self._assets_relative / document_id / filename
            images.append((token, output_path))
            line = f"![]({relative_path.as_posix()})"
            return [self._line_with_prefix(prefix, line, keep_blank=keep_blank)]

        if block_type == BLOCK_TYPE_DIVIDER:
            return [self._line_with_prefix(prefix, "---", keep_blank=keep_blank)]

        if block_type in (BLOCK_TYPE_QUOTE, BLOCK_TYPE_CALLOUT, BLOCK_TYPE_QUOTE_CONTAINER):
            return self._render_quote_container(
                block,
                parser,
                document_id,
                images,
                base_indent=base_indent,
                quote_prefix=quote_prefix,
            )

        if block_type in (BLOCK_TYPE_GRID, BLOCK_TYPE_GRID_COLUMN):
            children = parser.children_ids(block.get("block_id", ""))
            if children:
                return self._render_block_ids(
                    children,
                    parser,
                    document_id,
                    images,
                    base_indent=base_indent,
                    quote_prefix=quote_prefix,
                )
            return []

        fallback_text = parser.text_from_block(block)
        if fallback_text:
            return [self._line_with_prefix(prefix, fallback_text, keep_blank=keep_blank)]

        return []

    def _render_quote_container(
        self,
        block: dict,
        parser: DocxParser,
        document_id: str,
        images: list[tuple[str, Path]],
        *,
        base_indent: str,
        quote_prefix: str,
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
                base_indent=base_indent,
                quote_prefix=new_quote_prefix,
            )
            buffer.add_block(child_lines)

        return buffer.lines

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

    async def close(self) -> None:
        close = getattr(self._downloader, "close", None)
        if close:
            await close()


__all__ = ["DocxParser", "DocxTranscoder", "MediaDownloader"]
