from pathlib import Path

import pytest

from src.services.sheet_service import SheetMeta
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


class StubSheetService:
    async def list_sheet_ids(self, spreadsheet_token: str) -> list[str]:
        return ["sheet-1"]

    async def get_sheet_meta(self, spreadsheet_token: str, sheet_id: str) -> SheetMeta:
        return SheetMeta(
            sheet_id=sheet_id,
            title="阶段清单",
            row_count=3,
            column_count=3,
        )

    async def get_values(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        *,
        row_count: int,
        column_count: int,
    ) -> list[list[object]]:
        return [
            ["名称", "状态", "备注"],
            [
                [{"text": "需求文档"}],
                [{"text": "已完成"}],
                [{"text": "详情"}, {"text": "链接", "link": "https://example.com"}],
            ],
            ["立项书", "进行中", None],
        ]


class FailingSheetService:
    async def list_sheet_ids(self, spreadsheet_token: str) -> list[str]:
        return ["sheet-1"]

    async def get_sheet_meta(self, spreadsheet_token: str, sheet_id: str) -> SheetMeta:
        raise RuntimeError("sheet metadata unavailable")


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
    assert "2. 步骤二" in markdown
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

    assert "| - 列表项<br>&nbsp;&nbsp;- 子项 |" in markdown


@pytest.mark.asyncio
async def test_transcoder_table_supports_nested_cell_matrix(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["tbl"]},
        {
            "block_id": "tbl",
            "block_type": 31,
            "parent_id": "root",
            "table": {
                "cells": [["cell1", "cell2"], ["cell3", "cell4"]],
                "property": {"row_size": 2, "column_size": 2},
            },
        },
        {"block_id": "cell1", "block_type": 32, "parent_id": "tbl", "children": ["t1"]},
        {"block_id": "cell2", "block_type": 32, "parent_id": "tbl", "children": ["t2"]},
        {"block_id": "cell3", "block_type": 32, "parent_id": "tbl", "children": ["t3"]},
        {"block_id": "cell4", "block_type": 32, "parent_id": "tbl", "children": ["t4"]},
        {
            "block_id": "t1",
            "block_type": 2,
            "parent_id": "cell1",
            "text": {"elements": [{"text_run": {"content": "A"}}]},
        },
        {
            "block_id": "t2",
            "block_type": 2,
            "parent_id": "cell2",
            "text": {"elements": [{"text_run": {"content": "B"}}]},
        },
        {
            "block_id": "t3",
            "block_type": 2,
            "parent_id": "cell3",
            "text": {"elements": [{"text_run": {"content": "C"}}]},
        },
        {
            "block_id": "t4",
            "block_type": 2,
            "parent_id": "cell4",
            "text": {"elements": [{"text_run": {"content": "D"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-table", blocks)

    assert "| A | B |" in markdown
    assert "| C | D |" in markdown


@pytest.mark.asyncio
async def test_transcoder_table_cell_newlines_render_as_br(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["tbl"]},
        {
            "block_id": "tbl",
            "block_type": 31,
            "parent_id": "root",
            "table": {"cells": ["cell1"], "property": {"row_size": 1, "column_size": 1}},
        },
        {"block_id": "cell1", "block_type": 32, "parent_id": "tbl", "children": ["t1"]},
        {
            "block_id": "t1",
            "block_type": 2,
            "parent_id": "cell1",
            "text": {"elements": [{"text_run": {"content": "A\nB"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-table", blocks)

    assert "| A<br>B |" in markdown


@pytest.mark.asyncio
async def test_transcoder_ordered_list_keeps_sequence_and_nested_indent(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["o1", "o2"]},
        {
            "block_id": "o1",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {
                "style": {"sequence": "1"},
                "elements": [{"text_run": {"content": "主项"}}],
            },
            "children": ["b1"],
        },
        {
            "block_id": "b1",
            "block_type": 12,
            "parent_id": "o1",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "子项"}}],
            },
            "children": ["b1_1"],
        },
        {
            "block_id": "b1_1",
            "block_type": 12,
            "parent_id": "b1",
            "bullet": {
                "style": {},
                "elements": [{"text_run": {"content": "孙项"}}],
            },
        },
        {
            "block_id": "o2",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {
                "style": {"sequence": "auto"},
                "elements": [{"text_run": {"content": "次项"}}],
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-ordered", blocks)

    assert "1. 主项" in markdown
    assert "2. 次项" in markdown
    assert "   - 子项" in markdown
    assert "     - 孙项" in markdown


@pytest.mark.asyncio
async def test_transcoder_list_item_multiline_text_keeps_continuation_indent(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["o1"]},
        {
            "block_id": "o1",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {"style": {"sequence": "1"}, "elements": [{"text_run": {"content": "条目"}}]},
            "children": ["b1"],
        },
        {
            "block_id": "b1",
            "block_type": 12,
            "parent_id": "o1",
            "bullet": {"style": {}, "elements": [{"text_run": {"content": "建设方案\n附件.docx"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-list-multiline", blocks)

    assert "1. 条目" in markdown
    assert "   - 建设方案" in markdown
    assert "     附件.docx" in markdown


@pytest.mark.asyncio
async def test_transcoder_list_item_line_break_elements(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["b1"]},
        {
            "block_id": "b1",
            "block_type": 12,
            "parent_id": "root",
            "bullet": {
                "style": {},
                "elements": [
                    {"text_run": {"content": "第一行"}},
                    {"line_break": {}},
                    {"text_run": {"content": "第二行"}},
                ],
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-linebreak", blocks)

    assert "- 第一行" in markdown
    assert "  第二行" in markdown


@pytest.mark.asyncio
async def test_transcoder_text_block_multiline_keeps_prefix(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["o1", "t1"]},
        {
            "block_id": "o1",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {"style": {"sequence": "1"}, "elements": [{"text_run": {"content": "条目"}}]},
            "children": ["t1"],
        },
        {
            "block_id": "t1",
            "block_type": 2,
            "parent_id": "o1",
            "text": {"style": {}, "elements": [{"text_run": {"content": "第一行\n第二行"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-text-multiline", blocks)

    assert "   第一行" in markdown
    assert "   第二行" in markdown


@pytest.mark.asyncio
async def test_transcoder_heading_renders_children(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["h2"]},
        {
            "block_id": "h2",
            "block_type": 4,
            "parent_id": "root",
            "children": ["t1", "t2"],
            "heading2": {"elements": [{"text_run": {"content": "催办"}}]},
        },
        {
            "block_id": "t1",
            "block_type": 17,
            "parent_id": "h2",
            "todo": {"style": {"done": False}, "elements": [{"text_run": {"content": "事项一"}}]},
        },
        {
            "block_id": "t2",
            "block_type": 17,
            "parent_id": "h2",
            "todo": {"style": {"done": True}, "elements": [{"text_run": {"content": "事项二"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-heading", blocks)

    assert "## 催办" in markdown
    assert "- [ ] 事项一" in markdown
    assert "- [x] 事项二" in markdown


@pytest.mark.asyncio
async def test_transcoder_renders_mentions_and_reminders(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["p1"]},
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "elements": [
                    {"text_run": {"content": "任务："}},
                    {
                        "mention_doc": {
                            "title": "示例文档",
                            "url": "https://example.com/doc",
                            "text_element_style": {},
                        }
                    },
                    {
                        "mention_user": {
                            "user_id": "ou_test",
                            "text_element_style": {},
                        }
                    },
                    {
                        "reminder": {
                            "notify_time": "1700000000000",
                            "text_element_style": {},
                        }
                    },
                ]
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-mention", blocks)

    assert "[示例文档](https://example.com/doc)" in markdown
    assert "@ou_test" in markdown
    assert "提醒(" in markdown


@pytest.mark.asyncio
async def test_transcoder_renders_equation_elements(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["p1"]},
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "elements": [
                    {"text_run": {"content": "定义全域数据空间为 "}},
                    {"equation": {"content": "\\mathcal{D}", "text_element_style": {}}},
                    {"text_run": {"content": "。"}},
                ]
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-equation", blocks)

    assert "定义全域数据空间为 $\\mathcal{D}$。" in markdown


@pytest.mark.asyncio
async def test_transcoder_fallback_renders_unknown_element_with_text_and_link(
    tmp_path: Path,
) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["p1"]},
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "elements": [
                    {
                        "mention_sheet": {
                            "text": "预算表",
                            "link": "https://example.com/sheet",
                        }
                    }
                ]
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-unknown-element", blocks)

    assert "[预算表](https://example.com/sheet)" in markdown


@pytest.mark.asyncio
async def test_transcoder_renders_sheet_block_placeholder(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["sheet1"]},
        {
            "block_id": "sheet1",
            "block_type": 30,
            "parent_id": "root",
            "sheet": {"token": "sheet_token_1", "title": "阶段清单"},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-sheet", blocks)

    assert "阶段清单（sheet_token: sheet_token_1）" in markdown


@pytest.mark.asyncio
async def test_transcoder_renders_sheet_block_as_table(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["sheet1"]},
        {
            "block_id": "sheet1",
            "block_type": 30,
            "parent_id": "root",
            "sheet": {"token": "spreadsheet_token_1_sheet-1"},
        },
    ]

    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=StubDownloader(),
        sheet_service=StubSheetService(),
    )
    markdown = await transcoder.to_markdown("doc-sheet", blocks)

    assert "| 名称 | 状态 | 备注 |" in markdown
    assert "| 需求文档 | 已完成 | 详情[链接](https://example.com) |" in markdown
    assert "| 立项书 | 进行中 |  |" in markdown


@pytest.mark.asyncio
async def test_transcoder_sheet_block_supports_rich_cell_variants(tmp_path: Path) -> None:
    class RichSheetService:
        async def list_sheet_ids(self, spreadsheet_token: str) -> list[str]:
            return ["sheet-rich"]

        async def get_sheet_meta(self, spreadsheet_token: str, sheet_id: str) -> SheetMeta:
            return SheetMeta(
                sheet_id=sheet_id,
                title="复杂单元格",
                row_count=3,
                column_count=4,
            )

        async def get_values(
            self,
            spreadsheet_token: str,
            sheet_id: str,
            *,
            row_count: int,
            column_count: int,
        ) -> list[list[object]]:
            return [
                ["字段", "值", "链接", "备注"],
                [
                    [
                        {"text": "粗体", "segmentStyle": {"bold": True}},
                        {"text": " + 普通", "type": "text"},
                    ],
                    {"formattedValue": "42.0"},
                    {"text": "文档", "link": {"url": "https://example.com/doc?from=sheet"}},
                    {"richText": [{"text": "多行A"}, {"text": "\n"}, {"text": "B"}]},
                ],
                [
                    True,
                    3.14,
                    {"value": {"content": "嵌套值"}},
                    {"formula": "=SUM(A1:A2)"},
                ],
            ]

    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["sheet1"]},
        {
            "block_id": "sheet1",
            "block_type": 30,
            "parent_id": "root",
            "sheet": {"token": "spreadsheet_token_2_sheet-rich"},
        },
    ]

    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=StubDownloader(),
        sheet_service=RichSheetService(),
    )
    markdown = await transcoder.to_markdown("doc-sheet-rich", blocks)

    assert "| 字段 | 值 | 链接 | 备注 |" in markdown
    assert "| **粗体** + 普通 | 42.0 | [文档](https://example.com/doc?from=sheet) | 多行A<br>B |" in markdown
    assert "| True | 3.14 | 嵌套值 | =SUM(A1:A2) |" in markdown


@pytest.mark.asyncio
async def test_transcoder_sheet_block_falls_back_when_service_fails(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["sheet1"]},
        {
            "block_id": "sheet1",
            "block_type": 30,
            "parent_id": "root",
            "sheet": {"token": "spreadsheet_token_1_sheet-1", "title": "阶段清单"},
        },
    ]

    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=StubDownloader(),
        sheet_service=FailingSheetService(),
    )
    markdown = await transcoder.to_markdown("doc-sheet-fallback", blocks)

    assert "阶段清单（sheet_token: spreadsheet_token_1_sheet-1）" in markdown


@pytest.mark.asyncio
async def test_transcoder_renders_addons_mermaid_block(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["addon1"]},
        {
            "block_id": "addon1",
            "block_type": 40,
            "parent_id": "root",
            "add_ons": {
                "record": "{\"data\":\"graph TD\\nA-->B\"}",
                "component_type_id": "blk_631fefbbae02400430b8f9f4",
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-addon", blocks)

    assert "```mermaid" in markdown
    assert "graph TD" in markdown
    assert "A-->B" in markdown


@pytest.mark.asyncio
async def test_transcoder_todo_done_marker(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["t1", "t2"]},
        {
            "block_id": "t1",
            "block_type": 17,
            "parent_id": "root",
            "todo": {
                "style": {"done": True},
                "elements": [{"text_run": {"content": "完成事项"}}],
            },
        },
        {
            "block_id": "t2",
            "block_type": 17,
            "parent_id": "root",
            "todo": {
                "style": {"done": False},
                "elements": [{"text_run": {"content": "未完成事项"}}],
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-todo", blocks)

    assert "- [x] 完成事项" in markdown
    assert "- [ ] 未完成事项" in markdown


@pytest.mark.asyncio
async def test_transcoder_nested_text_container_in_todo(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["t1"]},
        {
            "block_id": "t1",
            "block_type": 17,
            "parent_id": "root",
            "todo": {
                "style": {"done": False},
                "text": {"elements": [{"text_run": {"content": "催办事项"}}]},
            },
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-nested-todo", blocks)

    assert "- [ ] 催办事项" in markdown


@pytest.mark.asyncio
async def test_transcoder_unknown_container_renders_children(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["v1"]},
        {"block_id": "v1", "block_type": 33, "parent_id": "root", "children": ["p1"]},
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "v1",
            "text": {"elements": [{"text_run": {"content": "内容"}}]},
        },
    ]

    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=StubDownloader())
    markdown = await transcoder.to_markdown("doc-view", blocks)

    assert "内容" in markdown


@pytest.mark.asyncio
async def test_transcoder_text_block_renders_children(tmp_path: Path) -> None:
    blocks = [
        {"block_id": "root", "block_type": 1, "children": ["t1"]},
        {
            "block_id": "t1",
            "block_type": 2,
            "parent_id": "root",
            "children": ["img1"],
            "text": {"elements": [{"text_run": {"content": "说明文本"}}]},
        },
        {
            "block_id": "img1",
            "block_type": 27,
            "parent_id": "t1",
            "image": {"token": "img-child"},
        },
    ]

    downloader = StubDownloader()
    transcoder = DocxTranscoder(assets_root=tmp_path, downloader=downloader)
    markdown = await transcoder.to_markdown("doc-child", blocks)

    assert "说明文本" in markdown
    assert "![](assets/doc-child/img-child.png)" in markdown


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


@pytest.mark.asyncio
async def test_transcoder_internal_full_coverage_document(tmp_path: Path) -> None:
    blocks = [
        {
            "block_id": "root",
            "block_type": 1,
            "children": [
                "h1",
                "p1",
                "bul1",
                "ord1",
                "todo1",
                "code1",
                "quote1",
                "callout1",
                "divider1",
                "tbl",
                "sheet1",
                "addon1",
                "file1",
                "img1",
                "view1",
            ],
        },
        {
            "block_id": "h1",
            "block_type": 3,
            "parent_id": "root",
            "heading1": {"elements": [{"text_run": {"content": "全量回归"}}]},
        },
        {
            "block_id": "p1",
            "block_type": 2,
            "parent_id": "root",
            "text": {
                "elements": [
                    {
                        "mention_doc": {
                            "title": "示例",
                            "url": "https://example.com/doc",
                            "text_element_style": {},
                        }
                    },
                    {"text_run": {"content": " "}},
                    {"mention_user": {"user_id": "ou_demo", "text_element_style": {}}},
                    {"text_run": {"content": " "}},
                    {"reminder": {"notify_time": "1700000000000", "text_element_style": {}}},
                    {"text_run": {"content": " "}},
                    {"equation": {"content": "x^2", "text_element_style": {}}},
                ]
            },
        },
        {
            "block_id": "bul1",
            "block_type": 12,
            "parent_id": "root",
            "bullet": {"style": {}, "elements": [{"text_run": {"content": "列表项"}}]},
        },
        {
            "block_id": "ord1",
            "block_type": 13,
            "parent_id": "root",
            "ordered": {"style": {"sequence": "1"}, "elements": [{"text_run": {"content": "步骤一"}}]},
        },
        {
            "block_id": "todo1",
            "block_type": 17,
            "parent_id": "root",
            "todo": {"style": {"done": True}, "elements": [{"text_run": {"content": "待办完成"}}]},
        },
        {
            "block_id": "code1",
            "block_type": 14,
            "parent_id": "root",
            "code": {"language": "python", "elements": [{"text_run": {"content": "print('ok')"}}]},
        },
        {
            "block_id": "quote1",
            "block_type": 15,
            "parent_id": "root",
            "quote": {"elements": [{"text_run": {"content": "引用块"}}]},
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
            "text": {"elements": [{"text_run": {"content": "提示块"}}]},
        },
        {"block_id": "divider1", "block_type": 22, "parent_id": "root"},
        {
            "block_id": "tbl",
            "block_type": 31,
            "parent_id": "root",
            "table": {"cells": ["c1", "c2", "c3", "c4"], "property": {"row_size": 2, "column_size": 2}},
        },
        {"block_id": "c1", "block_type": 32, "parent_id": "tbl", "children": ["t1"]},
        {"block_id": "c2", "block_type": 32, "parent_id": "tbl", "children": ["t2"]},
        {"block_id": "c3", "block_type": 32, "parent_id": "tbl", "children": ["t3"]},
        {"block_id": "c4", "block_type": 32, "parent_id": "tbl", "children": ["t4"]},
        {"block_id": "t1", "block_type": 2, "parent_id": "c1", "text": {"elements": [{"text_run": {"content": "H1"}}]}},
        {"block_id": "t2", "block_type": 2, "parent_id": "c2", "text": {"elements": [{"text_run": {"content": "H2"}}]}},
        {"block_id": "t3", "block_type": 2, "parent_id": "c3", "text": {"elements": [{"text_run": {"content": "R1"}}]}},
        {"block_id": "t4", "block_type": 2, "parent_id": "c4", "text": {"elements": [{"text_run": {"content": "R2"}}]}},
        {
            "block_id": "sheet1",
            "block_type": 30,
            "parent_id": "root",
            "sheet": {"token": "spreadsheet_token_1_sheet-1"},
        },
        {
            "block_id": "addon1",
            "block_type": 40,
            "parent_id": "root",
            "add_ons": {"record": "{\"data\":\"graph TD\\nA-->B\"}"},
        },
        {
            "block_id": "file1",
            "block_type": 23,
            "parent_id": "root",
            "file": {"token": "file-full", "name": "附件.docx"},
        },
        {
            "block_id": "img1",
            "block_type": 27,
            "parent_id": "root",
            "image": {"token": "img-full"},
        },
        {"block_id": "view1", "block_type": 33, "parent_id": "root", "children": ["view_text"]},
        {
            "block_id": "view_text",
            "block_type": 2,
            "parent_id": "view1",
            "text": {"elements": [{"text_run": {"content": "视图容器文本"}}]},
        },
    ]

    base_dir = tmp_path / "full"
    base_dir.mkdir(parents=True, exist_ok=True)
    file_downloader = StubFileDownloader()
    transcoder = DocxTranscoder(
        assets_root=tmp_path,
        downloader=StubDownloader(),
        file_downloader=file_downloader,
        sheet_service=StubSheetService(),
    )
    markdown = await transcoder.to_markdown(
        "doc-full",
        blocks,
        base_dir=base_dir,
        link_map={},
    )

    assert "# 全量回归" in markdown
    assert "[示例](https://example.com/doc)" in markdown
    assert "@ou_demo" in markdown
    assert "提醒(" in markdown
    assert "$x^2$" in markdown
    assert "- 列表项" in markdown
    assert "1. 步骤一" in markdown
    assert "- [x] 待办完成" in markdown
    assert "```python" in markdown
    assert "> 引用块" in markdown
    assert "> 提示块" in markdown
    assert "---" in markdown
    assert "| H1 | H2 |" in markdown
    assert "| R1 | R2 |" in markdown
    assert "| 名称 | 状态 | 备注 |" in markdown
    assert "```mermaid" in markdown
    assert "[附件.docx](attachments/附件.docx)" in markdown
    assert "![](assets/doc-full/img-full.png)" in markdown
    assert "视图容器文本" in markdown
