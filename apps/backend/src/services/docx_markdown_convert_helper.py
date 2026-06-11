from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Iterable

from src.services.transcoder import BLOCK_TYPE_TEXT

if TYPE_CHECKING:
    from src.services.docx_service import ConvertResult


_LIST_PREFIX_PATTERN = re.compile(
    r"^(?P<quote>(?:>\s*)*)(?P<indent>[ \t]+)(?P<body>(?:[-*+]\s+|\d+[.)]\s+).+)$"
)
_LIST_LINE_PATTERN = re.compile(r"^(?:>\s*)*(?:\t+| +)?(?:[-*+]\s+|\d+[.)]\s+).+")
_INDENTED_IMAGE_LINE_PATTERN = re.compile(
    r"^(?P<quote>(?:>\s*)*)(?P<indent>[ \t]+)(?P<image>!\[[^\]]*]\(.+\))\s*$"
)
_INDENTED_TEXT_LINE_PATTERN = re.compile(
    r"^(?P<quote>(?:>\s*)*)(?P<indent>[ \t]+)(?P<body>\S.*)$"
)
_CONTINUATION_PLACEHOLDER = "[[LARKSYNC_CONTINUATION]]"


def is_list_line(line: str) -> bool:
    return bool(_LIST_LINE_PATTERN.match(line))


def normalize_markdown_for_convert(markdown: str) -> str:
    lines = markdown.splitlines(keepends=True)
    if not lines:
        return markdown
    normalized: list[str] = []
    in_fence = False
    in_list_context = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            normalized.append(line)
            if stripped.strip():
                text = line.rstrip("\r\n")
                in_list_context = is_list_line(text)
            continue
        if in_fence:
            normalized.append(line)
            if stripped.strip():
                text = line.rstrip("\r\n")
                in_list_context = is_list_line(text)
            continue
        raw_line = line.rstrip("\r\n")
        image_line = _INDENTED_IMAGE_LINE_PATTERN.match(raw_line)
        if image_line and in_list_context:
            quote = image_line.group("quote")
            indent = normalize_indent_for_list(image_line.group("indent"))
            image = image_line.group("image")
            newline = "\n"
            if line.endswith("\r\n"):
                newline = "\r\n"
            elif line.endswith("\n"):
                newline = "\n"
            else:
                newline = ""
            line = f"{quote}{indent}- {image}{newline}"
            stripped = line.lstrip()
            raw_line = line.rstrip("\r\n")
        matched = _LIST_PREFIX_PATTERN.match(raw_line)
        if matched:
            indent = matched.group("indent")
            normalized_indent = normalize_indent_for_list(indent)
            quote = matched.group("quote")
            body = matched.group("body")
            newline = "\n"
            if line.endswith("\r\n"):
                newline = "\r\n"
            elif line.endswith("\n"):
                newline = "\n"
            else:
                newline = ""
            new_line = f"{quote}{normalized_indent}{body}{newline}"
            normalized.append(new_line)
            in_list_context = True
            continue
        if in_list_context:
            text_line = _INDENTED_TEXT_LINE_PATTERN.match(raw_line)
            if text_line:
                quote = text_line.group("quote")
                base_indent = normalize_indent_for_list(text_line.group("indent"))
                indent = base_indent + ("\t" if base_indent.count("\t") <= 1 else "")
                body = text_line.group("body")
                newline = "\n"
                if line.endswith("\r\n"):
                    newline = "\r\n"
                elif line.endswith("\n"):
                    newline = "\n"
                else:
                    newline = ""
                line = f"{quote}{indent}{_CONTINUATION_PLACEHOLDER}{body}{newline}"
                stripped = line.lstrip()
                in_list_context = True
        normalized.append(line)
        if stripped.strip():
            text = line.rstrip("\r\n")
            if is_list_line(text):
                in_list_context = True
            elif text.startswith((" ", "\t")) and in_list_context:
                in_list_context = True
            else:
                in_list_context = False
    return "".join(normalized)


def normalize_indent_for_list(indent: str) -> str:
    if not indent:
        return ""
    tab_count = indent.count("\t")
    space_count = indent.count(" ")
    if space_count <= 0:
        return "\t" * tab_count
    space_level = max(1, int((space_count - 1) // 2))
    level = tab_count + space_level
    return "\t" * level


def compile_placeholder_pattern(placeholders: Iterable[str]) -> re.Pattern[str] | None:
    tokens = sorted({token for token in placeholders if token}, key=len, reverse=True)
    if not tokens:
        return None
    return re.compile("|".join(re.escape(token) for token in tokens))


def find_placeholders(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [match.group(0) for match in pattern.finditer(text)]


def strip_placeholders_from_block(block: dict[str, Any], pattern: re.Pattern[str]) -> bool:
    updated = False
    for value in block.values():
        if not isinstance(value, dict):
            continue
        elements = value.get("elements")
        if not isinstance(elements, list):
            continue
        next_elements: list[Any] = []
        for element in elements:
            if not isinstance(element, dict):
                next_elements.append(element)
                continue
            text_run = element.get("text_run")
            if not isinstance(text_run, dict):
                next_elements.append(element)
                continue
            content = text_run.get("content")
            if not isinstance(content, str) or "[[LARKSYNC_IMAGE:" not in content:
                next_elements.append(element)
                continue
            cleaned = pattern.sub("", content)
            if cleaned != content:
                updated = True
            if not cleaned:
                continue
            patched_run = dict(text_run)
            patched_run["content"] = cleaned
            patched_element = dict(element)
            patched_element["text_run"] = patched_run
            next_elements.append(patched_element)
        value["elements"] = next_elements
    return updated


def set_block_plain_text(block: dict[str, Any], text: str) -> None:
    element = (
        []
        if not text
        else [
            {
                "text_run": {
                    "content": text,
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
    )
    for key, value in block.items():
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("elements"), list):
            value["elements"] = element
            return
    block["text"] = {"elements": element}


def plain_text_block(block_id: str, text: str) -> dict[str, Any]:
    block: dict[str, Any] = {"block_id": block_id, "block_type": BLOCK_TYPE_TEXT}
    set_block_plain_text(block, text)
    return block


def replace_continuation_placeholders(convert: ConvertResult) -> ConvertResult:
    if not convert.blocks:
        return convert

    converted_continuation_ids: set[str] = set()
    for block in convert.blocks:
        block_id = block.get("block_id")
        if not isinstance(block_id, str):
            continue
        block_has_placeholder = False
        placeholder_prefix_only = True
        combined_text_parts: list[str] = []
        preferred_elements: list[Any] | None = None

        for key, value in list(block.items()):
            if not isinstance(value, dict):
                continue
            elements = value.get("elements")
            if not isinstance(elements, list):
                continue

            next_elements: list[Any] = []
            element_updated = False
            local_placeholder = False
            for element in elements:
                if not isinstance(element, dict):
                    next_elements.append(element)
                    continue
                text_run = element.get("text_run")
                if not isinstance(text_run, dict):
                    next_elements.append(element)
                    continue
                content = text_run.get("content")
                if isinstance(content, str):
                    combined_text_parts.append(content)
                if not isinstance(content, str) or _CONTINUATION_PLACEHOLDER not in content:
                    next_elements.append(element)
                    continue
                local_placeholder = True
                element_updated = True
                cleaned = content.replace(_CONTINUATION_PLACEHOLDER, "")
                patched_run = dict(text_run)
                patched_run["content"] = cleaned
                patched_element = dict(element)
                patched_element["text_run"] = patched_run
                next_elements.append(patched_element)

            if local_placeholder:
                block_has_placeholder = True
                preferred_elements = next_elements
            if element_updated:
                patched_value = dict(value)
                patched_value["elements"] = next_elements
                block[key] = patched_value

        if not block_has_placeholder:
            continue
        combined_text = "".join(combined_text_parts)
        if combined_text.split(_CONTINUATION_PLACEHOLDER, 1)[0].strip():
            placeholder_prefix_only = False

        if block.get("block_type") in {12, 13, 17} and placeholder_prefix_only:
            new_block: dict[str, Any] = {
                "block_id": block_id,
                "block_type": BLOCK_TYPE_TEXT,
                "text": {"elements": preferred_elements or []},
            }
            children = block.get("children")
            if isinstance(children, list) and children:
                new_block["children"] = children
            block.clear()
            block.update(new_block)
            converted_continuation_ids.add(block_id)

    if converted_continuation_ids:
        reparent_converted_continuations(convert.blocks, converted_continuation_ids)

    return convert


def reparent_converted_continuations(
    blocks: list[dict[str, Any]], continuation_ids: set[str]
) -> None:
    if not blocks or not continuation_ids:
        return
    block_map = {
        block_id: block
        for block in blocks
        if isinstance((block_id := block.get("block_id")), str)
    }
    list_types = {12, 13, 17}
    for parent in blocks:
        children = list(parent.get("children") or [])
        if len(children) < 2:
            continue
        new_children: list[str] = []
        previous_kept: str | None = None
        moved = False
        for child_id in children:
            if child_id in continuation_ids and previous_kept:
                previous_block = block_map.get(previous_kept)
                if (
                    previous_block
                    and previous_block.get("block_type") in list_types
                    and should_attach_continuation_to_previous_list(previous_block)
                ):
                    previous_children = list(previous_block.get("children") or [])
                    previous_children.append(child_id)
                    previous_block["children"] = previous_children
                    moved = True
                    continue
            new_children.append(child_id)
            previous_kept = child_id
        if moved:
            parent["children"] = new_children


def should_attach_continuation_to_previous_list(block: dict[str, Any]) -> bool:
    text = extract_block_text_content(block).strip()
    if not text:
        return False
    if "\n" in text:
        return True
    return text.endswith((":", "："))


def extract_block_text_content(block: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in block.values():
        if not isinstance(value, dict):
            continue
        elements = value.get("elements")
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            text_run = element.get("text_run")
            if not isinstance(text_run, dict):
                continue
            content = text_run.get("content")
            if isinstance(content, str):
                parts.append(content)
    return "".join(parts)


def has_text_elements(block: dict[str, Any]) -> bool:
    for value in block.values():
        if not isinstance(value, dict):
            continue
        elements = value.get("elements")
        if isinstance(elements, list) and len(elements) > 0:
            return True
    return False


__all__ = [
    "compile_placeholder_pattern",
    "extract_block_text_content",
    "find_placeholders",
    "has_text_elements",
    "normalize_markdown_for_convert",
    "plain_text_block",
    "replace_continuation_placeholders",
    "set_block_plain_text",
    "strip_placeholders_from_block",
]
