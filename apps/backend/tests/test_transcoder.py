from pathlib import Path

import pytest

from src.services.transcoder import DocxTranscoder


class StubDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    async def download(self, file_token: str, output_path: Path) -> None:
        self.calls.append((file_token, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-image")


class FailingDownloader:
    async def download(self, file_token: str, output_path: Path) -> None:
        raise RuntimeError("download failed")


class StubFileDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Path]] = []

    async def download(self, file_token: str, file_name: str, target_dir: Path, mtime: float):
        self.calls.append((file_token, file_name, target_dir))
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / file_name).write_bytes(b"file")


@pytest.mark.asyncio
async def test_transcoder_handles_heading_bold_table_and_image(tmp_path: Path) -> None:
    blocks = [
        {
            "block_id": "root",
            "block_type": 1,
            "children": ["h1", "h2", "p1", "tbl", "img1"],
        },
        {
            "block_id": "h1",
            "block_type": 3,
            "parent_id": "root",
            "heading1": {
                "style": {},
                "elements": [{"text_run": {"content": "标题一"}}],
            },
        },
        {
            "block_id": "h2",
            "block_type": 4,
            "parent_id": "root",
            "heading2": {
                "style": {},
                "elements": [{"text_run": {"content": "标题二"}}],
            },
        },
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "style": {},
                "elements": [
                    {"text_run": {"content": "普通文字"}},
                    {
                        "text_run": {
                            "content": "加粗",
                            "text_element_style": {"bold": True},
                        }
                    },
                ],
            },
        },
        {
            "block_id": "tbl",
            "block_type": 31,
            "parent_id": "root",
            "table": {
                "cells": ["cell1", "cell2"],
                "property": {"row_size": 1, "column_size": 2},
            },
        },
        {
            "block_id": "cell1",
            "block_type": 32,
            "parent_id": "tbl",
            "children": ["cell1_text"],
        },
        {
            "block_id": "cell1_text",
            "block_type": 2,
            "parent_id": "cell1",
            "text": {
                "style": {},
                "elements": [{"text_run": {"content": "单元格1"}}],
            },
        },
        {
            "block_id": "cell2",
            "block_type": 32,
            "parent_id": "tbl",
            "children": ["cell2_text"],
        },
        {
            "block_id": "cell2_text",
            "block_type": 2,
            "parent_id": "cell2",
            "text": {
                "style": {},
                "elements": [{"text_run": {"content": "单元格2"}}],
            },
        },
        {
            "block_id": "img1",
            "block_type": 27,
            "parent_id": "root",
            "image": {"token": "img-token", "width": 100, "height": 100},
        },
    ]

    downloader = StubDownloader()
    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=downloader)

    markdown = await transcoder.to_markdown("doc-123", blocks)

    assert "# 标题一" in markdown
    assert "## 标题二" in markdown
    assert "普通文字**加粗**" in markdown
    assert "| 单元格1 | 单元格2 |" in markdown
    assert "![](assets/doc-123/img-token.png)" in markdown

    assert downloader.calls[0][0] == "img-token"
    assert (tmp_path / "doc-123" / "img-token.png").exists()


@pytest.mark.asyncio
async def test_transcoder_fallback_for_unknown_block(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["unknown"]},
        {
            "block_id": "unknown",
            "block_type": 99,
            "parent_id": "root",
            "text": {
                "style": {},
                "elements": [{"text_run": {"content": "未知块文本"}}],
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-unknown", blocks)
    assert "未知块文本" in markdown


@pytest.mark.asyncio
async def test_transcoder_handles_lists_quotes_code_and_todo(tmp_path: Path) -> None:
    blocks = [
        {
            "block_id": "root",
            "block_type": 1,
            "children": [
                "bul1",
                "bul2",
                "ord1",
                "ord2",
                "todo1",
                "code1",
                "quote1",
                "callout1",
                "divider1",
            ],
        },
        {
            "block_id": "bul1",
            "block_type": 12,
            "parent_id": "root",
            "children": ["bul1_child"],
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "列表一"}}],
            },
        },
        {
            "block_id": "bul1_child",
            "block_type": 12,
            "parent_id": "bul1",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "子项"}}],
            },
        },
        {
            "block_id": "bul2",
            "block_type": 12,
            "parent_id": "root",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "列表二"}}],
            },
        },
        {
            "block_id": "ord1",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {
                "style": {},
                "elements": [{"text_run": {"content": "步骤一"}}],
            },
        },
        {
            "block_id": "ord2",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {
                "style": {},
                "elements": [{"text_run": {"content": "步骤二"}}],
            },
        },
        {
            "block_id": "todo1",
            "block_type": 17,
            "parent_id": "root",
            "todo": {
                "style": {},
                "elements": [{"text_run": {"content": "待办任务"}}],
            },
        },
        {
            "block_id": "code1",
            "block_type": 14,
            "parent_id": "root",
            "code": {
                "style": {},
                "elements": [{"text_run": {"content": "print('hi')"}}],
            },
        },
        {
            "block_id": "quote1",
            "block_type": 15,
            "parent_id": "root",
            "quote": {
                "style": {},
                "elements": [{"text_run": {"content": "引用内容"}}],
            },
        },
        {
            "block_id": "callout1",
            "block_type": 19,
            "parent_id": "root",
            "children": ["callout_text"],
        },
        {
            "block_id": "callout_text",
            "block_type": 2,
            "parent_id": "callout1",
            "text": {
                "style": {},
                "elements": [{"text_run": {"content": "提示内容"}}],
            },
        },
        {
            "block_id": "divider1",
            "block_type": 22,
            "parent_id": "root",
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-list", blocks)

    assert "- 列表一" in markdown
    assert "  - 子项" in markdown
    assert "- 列表二" in markdown
    assert "1. 步骤一" in markdown
    assert "1. 步骤二" in markdown
    assert "- [ ] 待办任务" in markdown
    assert "```" in markdown
    assert "print('hi')" in markdown
    assert "> 引用内容" in markdown
    assert "> 提示内容" in markdown
    assert "---" in markdown


@pytest.mark.asyncio
async def test_transcoder_table_cell_collects_nested_text(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["tbl"]},
        {
            "block_id": "tbl",
            "block_type": 31,
            "parent_id": "root",
            "table": {"cells": ["cell1"], "property": {"row_size": 1, "column_size": 1}},
        },
        {"block_id": "cell1", "block_type": 32, "parent_id": "tbl", "children": ["bul1"]},
        {
            "block_id": "bul1",
            "block_type": 12,
            "parent_id": "cell1",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "列表项"}}],
            },
            "children": ["bul_child"],
        },
        {
            "block_id": "bul_child",
            "block_type": 12,
            "parent_id": "bul1",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "子项"}}],
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-table", blocks)

    assert "| 列表项 子项 |" in markdown


@pytest.mark.asyncio
async def test_transcoder_rewrites_links_to_local_paths(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["p1"]},
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "style": {},
                "elements": [
                    {
                        "text_run": {
                            "content": "链接",
                            "text_element_style": {
                                "link": {
                                    "url": "https://example.feishu.cn/docx/doccnABC123"
                                }
                            },
                        }
                    }
                ],
            },
        },
    ]

    base_dir = tmp_path / "docs"
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = tmp_path / "Doc.md"
    link_map = {"doccnABC123": target_path}

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown(
        "doc-link",
        blocks,
        base_dir=base_dir,
        link_map=link_map,
    )

    assert "[链接](" in markdown
    assert "Doc.md" in markdown


@pytest.mark.asyncio
async def test_transcoder_downloads_attachment_blocks(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["file1"]},
        {
            "block_id": "file1",
            "block_type": 23,
            "parent_id": "root",
            "file": {"token": "file-token", "name": "附件.pdf"},
        },
    ]

    base_dir = tmp_path / "doc"
    base_dir.mkdir(parents=True, exist_ok=True)
    file_downloader = StubFileDownloader()
    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=StubDownloader(),
        file_downloader=file_downloader,
    )
    markdown = await transcoder.to_markdown(
        "doc-attach",
        blocks,
        base_dir=base_dir,
        link_map={},
    )

    assert "[附件.pdf](attachments/附件.pdf)" in markdown
    assert file_downloader.calls[0][0] == "file-token"
    assert (base_dir / "attachments" / "附件.pdf").exists()


@pytest.mark.asyncio
async def test_transcoder_falls_back_when_image_download_fails(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["img1"]},
        {
            "block_id": "img1",
            "block_type": 27,
            "parent_id": "root",
            "image": {"token": "img-token"},
        },
    ]

    file_downloader = StubFileDownloader()
    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=FailingDownloader(),
        file_downloader=file_downloader,
    )
    markdown = await transcoder.to_markdown(
        "doc-image",
        blocks,
        base_dir=tmp_path,
        link_map={},
    )

    assert "![](assets/doc-image/img-token.png)" in markdown
    assert file_downloader.calls[0][0] == "img-token"
