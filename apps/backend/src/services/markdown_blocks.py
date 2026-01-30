from __future__ import annotations

import hashlib
import re

_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?[-]{3,}:?\s*(\|\s*:?[-]{3,}:?\s*)*\|?\s*$")
_LIST_RE = re.compile(r"^\s{0,3}([*+-]|\d+\.)\s+")
_HEADING_RE = re.compile(r"^#{1,6}\s+")


def split_markdown_blocks(markdown: str) -> list[str]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    buffer: list[str] = []
    in_code = False
    fence = ""
    i = 0

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer:
            blocks.append("\n".join(buffer).strip("\n"))
            buffer = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                flush_buffer()
                in_code = True
                fence = stripped[:3]
                buffer.append(line)
            else:
                buffer.append(line)
                in_code = False
                fence = ""
                flush_buffer()
            i += 1
            continue

        if in_code:
            buffer.append(line)
            i += 1
            continue

        if stripped == "":
            flush_buffer()
            i += 1
            continue

        if _is_table_header(line) and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            flush_buffer()
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines):
                row_line = lines[i]
                row_strip = row_line.strip()
                if row_strip == "":
                    break
                if row_strip.startswith("```"):
                    break
                if _is_table_separator(row_line):
                    break
                if "|" not in row_line:
                    break
                table_lines.append(row_line)
                i += 1
            blocks.append("\n".join(table_lines).strip("\n"))
            continue

        if _is_list_line(line):
            flush_buffer()
            list_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_strip = next_line.strip()
                if next_strip == "":
                    list_lines.append(next_line)
                    i += 1
                    continue
                if _is_list_line(next_line):
                    list_lines.append(next_line)
                    i += 1
                    continue
                if next_line.startswith(" ") or next_line.startswith("\t"):
                    list_lines.append(next_line)
                    i += 1
                    continue
                break
            blocks.append("\n".join(list_lines).strip("\n"))
            continue

        if stripped.startswith(">"):
            flush_buffer()
            quote_lines = [line]
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote_lines.append(lines[i])
                i += 1
            blocks.append("\n".join(quote_lines).strip("\n"))
            continue

        if _HEADING_RE.match(stripped):
            flush_buffer()
            blocks.append(line.strip("\n"))
            i += 1
            continue

        buffer.append(line)
        i += 1

    flush_buffer()
    return blocks


def normalize_block(block: str) -> str:
    return "\n".join([line.rstrip() for line in block.strip().split("\n")])


def hash_block(block: str) -> str:
    normalized = normalize_block(block)
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

def _is_table_separator(line: str) -> bool:
    return bool(_TABLE_SEPARATOR_RE.match(line.strip()))


def _is_table_header(line: str) -> bool:
    if "|" not in line:
        return False
    return not _is_table_separator(line)


def _is_list_line(line: str) -> bool:
    return bool(_LIST_RE.match(line))


__all__ = ["split_markdown_blocks", "normalize_block", "hash_block"]
