from src.services.markdown_blocks import split_markdown_blocks


def test_split_markdown_blocks_basic() -> None:
    markdown = "# Title\n\nParagraph one.\n\n- item1\n- item2\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n```python\nprint('hi')\n```\n"
    blocks = split_markdown_blocks(markdown)
    assert blocks[0] == "# Title"
    assert "Paragraph one." in blocks[1]
    assert blocks[2].startswith("- item1")
    assert blocks[3].startswith("| A | B |")
    assert blocks[4].startswith("```python")


def test_split_markdown_blocks_keeps_quotes() -> None:
    markdown = "> quote line 1\n> quote line 2\n\nNext"
    blocks = split_markdown_blocks(markdown)
    assert blocks[0].startswith("> quote")
    assert blocks[1] == "Next"
