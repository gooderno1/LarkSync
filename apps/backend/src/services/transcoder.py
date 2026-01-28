from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from src.services.feishu_client import FeishuClient


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
        self._block_map = {block.get("block_id"): block for block in blocks}

    def resolve_order(self) -> list[str]:
        root = self._find_root()
        if root:
            children = root.get("children") or []
            return [child for child in children if child in self._block_map]
        return [block.get("block_id") for block in self._blocks if block.get("block_id")]

    def _find_root(self) -> dict | None:
        for block in self._blocks:
            if block.get("block_type") == 1:
                return block
        return None

    def get_block(self, block_id: str) -> dict | None:
        return self._block_map.get(block_id)

    def text_from_block(self, block: dict) -> str:
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
        return "".join(parts).strip()

    def _resolve_text_block(self, block: dict) -> dict | None:
        if "text" in block:
            return block.get("text")
        heading_field = self._heading_field(block.get("block_type"))
        if heading_field and heading_field in block:
            return block.get(heading_field)
        return None

    def _heading_field(self, block_type: int | None) -> str | None:
        if not block_type:
            return None
        if 3 <= block_type <= 11:
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
        markdown_blocks: list[str] = []
        images: list[tuple[str, Path]] = []

        for block_id in ordered_ids:
            block = parser.get_block(block_id)
            if not block:
                continue
            rendered, image = self._render_block(block, parser, document_id)
            if rendered:
                markdown_blocks.append(rendered)
            if image:
                images.append(image)

        for token, path in images:
            await self._downloader.download(token, path)

        return "\n\n".join(markdown_blocks).strip()

    def _render_block(
        self, block: dict, parser: DocxParser, document_id: str
    ) -> tuple[str | None, tuple[str, Path] | None]:
        block_type = block.get("block_type")

        if block_type in (3, 4, 5, 6, 7, 8, 9, 10, 11):
            level = block_type - 2
            text = parser.text_from_block(block)
            return f"{'#' * level} {text}".strip(), None

        if block_type == 2:
            text = parser.text_from_block(block)
            return text or None, None

        if block_type == 31:
            table_md = parser.table_markdown(block)
            return table_md or None, None

        if block_type == 27:
            image = block.get("image") or {}
            token = image.get("token")
            if not token:
                return None, None
            filename = f"{token}.png"
            output_path = self._assets_root / document_id / filename
            relative_path = self._assets_relative / document_id / filename
            return f"![]({relative_path.as_posix()})", (token, output_path)

        fallback_text = parser.text_from_block(block)
        if fallback_text:
            return fallback_text, None

        return None, None

    async def close(self) -> None:
        close = getattr(self._downloader, "close", None)
        if close:
            await close()


__all__ = ["DocxParser", "DocxTranscoder", "MediaDownloader"]
