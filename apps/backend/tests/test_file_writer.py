from pathlib import Path

from src.services.file_writer import FileWriter


def test_write_markdown_sets_mtime(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "doc.md"
    content = "# 标题"
    mtime = 1700000000.0

    FileWriter.write_markdown(target, content, mtime)

    assert target.read_text(encoding="utf-8") == content
    assert abs(target.stat().st_mtime - mtime) < 1.0
