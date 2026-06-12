from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import unquote, urlsplit

from loguru import logger

from src.services.transcoder import (
    BLOCK_TYPE_FILE,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_TEXT,
    DocxParser,
)

NormalizeImageRef = Callable[[str], str]
IsRemoteImage = Callable[[str], bool]
IsRemoteLink = Callable[[str], bool]
HashText = Callable[[str], str]
FindFigureIdForOffset = Callable[[str, int], str | None]
FindLocalFigureAsset = Callable[[str | Path | None, str | None], Path | None]
ExtractFigureIdFromImageRef = Callable[[str], str | None]
WriteDataImageToTemp = Callable[[str, str | None], Path | None]
CompilePlaceholderPattern = Callable[[list[str] | tuple[str, ...] | set[str]], re.Pattern[str] | None]
FindPlaceholders = Callable[[str, re.Pattern[str]], list[str]]
StripPlaceholdersFromBlock = Callable[[dict[str, Any], re.Pattern[str]], bool]
SetBlockPlainText = Callable[[dict[str, Any], str], None]
HasTextElements = Callable[[dict[str, Any]], bool]

_HTML_IMAGE_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
_HTML_IMAGE_SRC_PATTERN = re.compile(
    r"""\bsrc\s*=\s*(?P<quote>["'])(?P<src>.*?)(?P=quote)""",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class MarkdownInlineResource:
    raw: str
    ref: str


class DocxMarkdownAssetService:
    def __init__(
        self,
        *,
        normalize_image_ref: NormalizeImageRef,
        is_remote_image: IsRemoteImage,
        is_remote_link: IsRemoteLink,
        hash_text: HashText,
        find_figure_id_for_offset: FindFigureIdForOffset,
        find_local_figure_asset: FindLocalFigureAsset,
        extract_figure_id_from_image_ref: ExtractFigureIdFromImageRef,
        write_data_image_to_temp: WriteDataImageToTemp,
        compile_placeholder_pattern: CompilePlaceholderPattern,
        find_placeholders: FindPlaceholders,
        strip_placeholders_from_block: StripPlaceholdersFromBlock,
        set_block_plain_text: SetBlockPlainText,
        has_text_elements: HasTextElements,
    ) -> None:
        self._normalize_image_ref = normalize_image_ref
        self._is_remote_image = is_remote_image
        self._is_remote_link = is_remote_link
        self._hash_text = hash_text
        self._find_figure_id_for_offset = find_figure_id_for_offset
        self._find_local_figure_asset = find_local_figure_asset
        self._extract_figure_id_from_image_ref = extract_figure_id_from_image_ref
        self._write_data_image_to_temp = write_data_image_to_temp
        self._compile_placeholder_pattern = compile_placeholder_pattern
        self._find_placeholders = find_placeholders
        self._strip_placeholders_from_block = strip_placeholders_from_block
        self._set_block_plain_text = set_block_plain_text
        self._has_text_elements = has_text_elements

    def build_image_placeholders(
        self,
        markdown: str,
        base_path: str | Path | None,
    ) -> tuple[str, dict[str, str], dict[str, Path]]:
        processed = markdown
        placeholders: dict[str, str] = {}
        image_paths: dict[str, Path] = {}
        for item in _iter_markdown_inline_resources(markdown, image=True):
            raw = item.raw
            ref = self._normalize_image_ref(item.ref)
            if self._is_remote_image(ref):
                continue
            image_path = self.resolve_markdown_image_path(ref, base_path)
            if not image_path.exists() or not image_path.is_file():
                processed = processed.replace(raw, f"[图片缺失: {ref}]", 1)
                continue
            placeholder = f"[[LARKSYNC_IMAGE:{self._hash_text(str(image_path))}]]"
            placeholders[placeholder] = ref
            image_paths[placeholder] = image_path
            processed = processed.replace(raw, placeholder, 1)

        for match in _HTML_IMAGE_PATTERN.finditer(markdown):
            raw = match.group(0)
            src_match = _HTML_IMAGE_SRC_PATTERN.search(raw)
            if not src_match:
                continue
            ref = src_match.group("src").strip()
            if self._is_remote_link(ref) and not ref.lower().startswith("data:"):
                continue
            image_path = self.resolve_html_image_path(
                ref=ref,
                markdown=markdown,
                offset=match.start(),
                base_path=base_path,
            )
            if image_path is None or not image_path.exists() or not image_path.is_file():
                processed = processed.replace(raw, "[图片缺失: 嵌入图片]", 1)
                continue
            placeholder = f"[[LARKSYNC_IMAGE:{self._hash_text(str(image_path))}]]"
            placeholders[placeholder] = ref
            image_paths[placeholder] = image_path
            processed = processed.replace(raw, placeholder, 1)
        return processed, placeholders, image_paths

    def build_file_placeholders(
        self,
        markdown: str,
        base_path: str | Path | None,
    ) -> tuple[str, dict[str, str], dict[str, Path]]:
        processed = markdown
        placeholders: dict[str, str] = {}
        file_paths: dict[str, Path] = {}
        for item in _iter_markdown_inline_resources(markdown, image=False):
            raw = item.raw
            ref = self._normalize_image_ref(item.ref)
            if self._is_remote_link(ref):
                continue
            file_path = self.resolve_image_path(ref, base_path)
            if (
                not file_path.exists()
                or not file_path.is_file()
                or file_path.suffix.lower() == ".md"
            ):
                continue
            placeholder = f"[[LARKSYNC_FILE:{self._hash_text(str(file_path))}]]"
            placeholders[placeholder] = ref
            file_paths[placeholder] = file_path
            processed = processed.replace(raw, placeholder, 1)
        return processed, placeholders, file_paths

    def resolve_html_image_path(
        self,
        *,
        ref: str,
        markdown: str,
        offset: int,
        base_path: str | Path | None,
    ) -> Path | None:
        figure_id = self._find_figure_id_for_offset(markdown, offset)
        local_figure = self._find_local_figure_asset(base_path, figure_id)
        if local_figure is not None:
            return local_figure
        if ref.lower().startswith("data:"):
            return self._write_data_image_to_temp(ref, figure_id)
        if self._is_remote_link(ref):
            return None
        image_path = self.resolve_image_path(ref, base_path)
        if image_path.exists() and image_path.is_file():
            return image_path
        return None

    def resolve_markdown_image_path(
        self,
        ref: str,
        base_path: str | Path | None,
    ) -> Path:
        image_path = self.resolve_image_path(ref, base_path)
        if image_path.exists() and image_path.is_file():
            return image_path
        local_figure = self._find_local_figure_asset(
            base_path,
            self._extract_figure_id_from_image_ref(ref),
        )
        if local_figure is not None:
            logger.info(
                "Markdown 图片路径失效，已按图号匹配本地资源: ref={} resolved={}",
                ref,
                local_figure,
            )
            return local_figure
        return image_path

    def replace_placeholders_with_images(
        self,
        convert: Any,
        *,
        placeholders: dict[str, str],
        image_paths: dict[str, Path],
        file_placeholders: dict[str, str] | None = None,
        file_paths: dict[str, Path] | None = None,
    ) -> Any:
        file_placeholders = file_placeholders or {}
        file_paths = file_paths or {}
        if not placeholders and not file_placeholders:
            return convert

        blocks: list[dict[str, Any]] = [dict(block) for block in convert.blocks]
        parser = DocxParser(blocks)
        first_level_ids = list(convert.first_level_block_ids)
        block_map = {
            block_id: block
            for block in blocks
            if isinstance((block_id := block.get("block_id")), str)
        }
        parent_map: dict[str, str] = {}
        for parent in blocks:
            parent_id = parent.get("block_id")
            if not isinstance(parent_id, str):
                continue
            for child_id in parent.get("children") or []:
                if isinstance(child_id, str):
                    parent_map[child_id] = parent_id

        image_pattern = self._compile_placeholder_pattern(placeholders.keys())
        file_pattern = self._compile_placeholder_pattern(file_placeholders.keys())
        placeholder_pattern = self._compile_placeholder_pattern(
            list(placeholders.keys()) + list(file_placeholders.keys())
        )
        if placeholder_pattern is None:
            return convert

        def resolve_placeholder_type(token: str) -> str | None:
            if image_pattern and image_pattern.fullmatch(token):
                return "image"
            if file_pattern and file_pattern.fullmatch(token):
                return "file"
            return None

        def path_for_placeholder(token: str) -> Path | None:
            if token in image_paths:
                return image_paths[token]
            return file_paths.get(token)

        def build_asset_block(block_id: str, token: str) -> tuple[dict[str, Any], Path] | None:
            asset_type = resolve_placeholder_type(token)
            asset_path = path_for_placeholder(token)
            if asset_type is None or asset_path is None:
                return None
            if asset_type == "image":
                return (
                    {"block_id": block_id, "block_type": BLOCK_TYPE_IMAGE, "image": {}},
                    asset_path,
                )
            return (
                {"block_id": block_id, "block_type": BLOCK_TYPE_FILE, "file": {}},
                asset_path,
            )

        def insert_siblings_after(after_block_id: str, sibling_ids: list[str]) -> None:
            if not sibling_ids:
                return
            if after_block_id in first_level_ids:
                insert_at = first_level_ids.index(after_block_id) + 1
                first_level_ids[insert_at:insert_at] = sibling_ids
                return
            parent_id = parent_map.get(after_block_id)
            if not parent_id:
                first_level_ids.extend(sibling_ids)
                return
            parent_block = block_map.get(parent_id)
            if parent_block is None:
                first_level_ids.extend(sibling_ids)
                return
            parent_children = list(parent_block.get("children") or [])
            insert_at = (
                parent_children.index(after_block_id) + 1
                if after_block_id in parent_children
                else len(parent_children)
            )
            parent_children[insert_at:insert_at] = sibling_ids
            parent_block["children"] = parent_children
            for sibling_id in sibling_ids:
                parent_map[sibling_id] = parent_id

        appended_blocks: list[dict[str, Any]] = []
        image_block_paths: dict[str, Path] = {}
        file_block_paths: dict[str, Path] = {}
        replaced = False

        for block in blocks:
            block_id = block.get("block_id")
            if not isinstance(block_id, str):
                continue
            text = parser.text_from_block(block, strip=False)
            if not text or "[[LARKSYNC_" not in text:
                continue
            matched = self._find_placeholders(text, placeholder_pattern)
            if not matched:
                continue
            replaced = True

            if not self._strip_placeholders_from_block(block, placeholder_pattern):
                fallback_text = placeholder_pattern.sub("", text).strip()
                self._set_block_plain_text(block, fallback_text)

            cleaned_text = parser.text_from_block(block, strip=True)
            block_type = block.get("block_type")
            existing_children = list(block.get("children") or [])
            sibling_placeholders = list(matched)
            if (
                block_type in {BLOCK_TYPE_TEXT, 12, 13, 17}
                and not cleaned_text
                and not existing_children
            ):
                first = sibling_placeholders.pop(0)
                built = build_asset_block(block_id, first)
                if built is not None:
                    block.clear()
                    asset_block, asset_path = built
                    block.update(asset_block)
                    if block.get("block_type") == BLOCK_TYPE_IMAGE:
                        image_block_paths[block_id] = asset_path
                    else:
                        file_block_paths[block_id] = asset_path
            elif block_type in {12, 13, 17} and not self._has_text_elements(block):
                self._set_block_plain_text(block, " ")

            sibling_ids: list[str] = []
            for placeholder in sibling_placeholders:
                asset_type = resolve_placeholder_type(placeholder)
                if asset_type is None:
                    continue
                asset_prefix = "img" if asset_type == "image" else "file"
                asset_block_id = f"{asset_prefix}_{uuid.uuid4().hex}"
                built = build_asset_block(asset_block_id, placeholder)
                if built is None:
                    continue
                asset_block, asset_path = built
                sibling_ids.append(asset_block_id)
                appended_blocks.append(asset_block)
                if asset_block.get("block_type") == BLOCK_TYPE_IMAGE:
                    image_block_paths[asset_block_id] = asset_path
                else:
                    file_block_paths[asset_block_id] = asset_path

            if sibling_ids and block_type in {12, 13, 17} and cleaned_text:
                children = list(block.get("children") or [])
                children.extend(sibling_ids)
                block["children"] = children
                for sibling_id in sibling_ids:
                    parent_map[sibling_id] = block_id
            else:
                insert_siblings_after(block_id, sibling_ids)

        if not replaced:
            return convert

        blocks.extend(appended_blocks)
        convert.image_paths.update(image_block_paths)
        convert.file_paths.update(file_block_paths)
        return type(convert)(
            first_level_block_ids=first_level_ids,
            blocks=blocks,
            image_paths=convert.image_paths,
            file_paths=convert.file_paths,
        )

    @staticmethod
    def resolve_image_path(ref: str, base_path: str | Path | None) -> Path:
        normalized = ref.strip()
        if normalized.lower().startswith("file://"):
            parsed = urlsplit(normalized)
            normalized = parsed.path or ""
            if parsed.netloc:
                normalized = f"//{parsed.netloc}{normalized}"
        else:
            normalized = normalized.split("#", 1)[0].split("?", 1)[0]
        normalized = unquote(normalized).replace("\\ ", " ").strip()
        if (
            normalized.startswith("/")
            and len(normalized) >= 3
            and normalized[1].isalpha()
            and normalized[2] == ":"
        ):
            normalized = normalized[1:]
        path = Path(normalized)
        if not path.is_absolute() and base_path:
            base = Path(base_path)
            if base.is_file():
                base = base.parent
            path = base / path
        return path.expanduser()


def _iter_markdown_inline_resources(
    markdown: str,
    *,
    image: bool,
) -> Iterator[MarkdownInlineResource]:
    fenced_ranges = _collect_fenced_code_ranges(markdown)
    cursor = 0
    marker = "![" if image else "["
    while cursor < len(markdown):
        start = markdown.find(marker, cursor)
        if start < 0:
            break
        fenced_end = _range_end_containing(start, fenced_ranges)
        if fenced_end is not None:
            cursor = fenced_end
            continue
        if _is_escaped(markdown, start):
            cursor = start + len(marker)
            continue
        if not image and start > 0 and markdown[start - 1] == "!":
            cursor = start + 1
            continue

        label_open = start + 1 if image else start
        label_close = _find_closing_label(markdown, label_open)
        if label_close < 0:
            cursor = start + len(marker)
            continue

        open_paren = label_close + 1
        if open_paren >= len(markdown) or markdown[open_paren] != "(":
            cursor = label_close + 1
            continue

        close_paren = _find_closing_paren(markdown, open_paren)
        if close_paren < 0:
            cursor = open_paren + 1
            continue

        yield MarkdownInlineResource(
            raw=markdown[start : close_paren + 1],
            ref=markdown[open_paren + 1 : close_paren],
        )
        cursor = close_paren + 1


def _collect_fenced_code_ranges(markdown: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    offset = 0
    fence_marker: str | None = None
    fence_start = 0
    for line in markdown.splitlines(keepends=True):
        stripped = line.lstrip(" ")
        marker = None
        if stripped.startswith("```"):
            marker = "```"
        elif stripped.startswith("~~~"):
            marker = "~~~"
        if marker is not None:
            if fence_marker is None:
                fence_marker = marker
                fence_start = offset
            elif marker == fence_marker:
                ranges.append((fence_start, offset + len(line)))
                fence_marker = None
        offset += len(line)
    if fence_marker is not None:
        ranges.append((fence_start, len(markdown)))
    return ranges


def _range_end_containing(index: int, ranges: list[tuple[int, int]]) -> int | None:
    for start, end in ranges:
        if start <= index < end:
            return end
    return None


def _find_closing_label(markdown: str, open_bracket: int) -> int:
    depth = 1
    cursor = open_bracket + 1
    while cursor < len(markdown):
        char = markdown[cursor]
        if _is_escaped(markdown, cursor):
            cursor += 1
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return -1


def _find_closing_paren(markdown: str, open_paren: int) -> int:
    depth = 0
    cursor = open_paren + 1
    quote: str | None = None
    in_angle = False
    while cursor < len(markdown):
        char = markdown[cursor]
        if _is_escaped(markdown, cursor):
            cursor += 1
            continue
        if quote is not None:
            if char == quote:
                quote = None
            cursor += 1
            continue
        if in_angle:
            if char == ">":
                in_angle = False
            cursor += 1
            continue
        if char == "<":
            in_angle = True
            cursor += 1
            continue
        if char in {"'", '"'}:
            quote = char
            cursor += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                return cursor
            depth -= 1
        cursor += 1
    return -1


def _is_escaped(text: str, index: int) -> bool:
    slash_count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        slash_count += 1
        cursor -= 1
    return slash_count % 2 == 1


__all__ = ["DocxMarkdownAssetService"]
