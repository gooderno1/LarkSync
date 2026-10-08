from pathlib import Path

import pytest

from src.services.sync_link_service import SyncLinkItem
from src.services.sync_task_browse_service import browse_task_entries
from test_sync_path_mode import make_task, rule


def test_browse_merges_local_and_cloud_links_and_shows_effective_mode(tmp_path: Path) -> None:
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts/a.md").write_text("a", encoding="utf-8")
    (tmp_path / "one.pdf").write_bytes(b"pdf")
    (tmp_path / "assets").mkdir()
    task = make_task(tmp_path, rules=[rule("drafts", "upload_only")])
    links = [SyncLinkItem(local_path=str(tmp_path / "cloud/doc.md"), cloud_token="doc",
                          cloud_type="docx", task_id=task.id, updated_at=1)]
    response = browse_task_entries(task, links, path="", search="", offset=0, limit=100)
    assert [item.path for item in response.items] == ["cloud", "drafts", "one.pdf"]
    child = browse_task_entries(task, links, path="drafts", search="", offset=0, limit=100)
    assert child.items[0].sync_mode == "upload_only"
    remote = browse_task_entries(task, links, path="cloud", search="", offset=0, limit=100)
    assert remote.items[0].path == "cloud/doc.md"
    assert response.total == 3


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside", "a/../../outside"])
def test_browse_cannot_escape_task_root(tmp_path: Path, path: str) -> None:
    with pytest.raises(ValueError):
        browse_task_entries(make_task(tmp_path), [], path=path, search="", offset=0, limit=100)


def test_browse_pages_and_filters_without_duplicate_entries(tmp_path: Path) -> None:
    for index in range(4):
        (tmp_path / f"design-{index}.md").write_text("a", encoding="utf-8")
    result = browse_task_entries(make_task(tmp_path), [], path="", search="design", offset=1, limit=2)
    assert result.total == 4
    assert [item.path for item in result.items] == ["design-1.md", "design-2.md"]
