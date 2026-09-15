from pathlib import Path
import os

import pytest

from src.services.sync_path_policy import should_ignore_sync_path


@pytest.mark.parametrize("relative", [
    "node_modules", "node_modules/pkg/index.js",
    "project/node_modules/pkg/README.md", "project/NODE_MODULES/pkg/index.js",
])
def test_dependency_directories_are_ignored_by_default(tmp_path: Path, relative: str) -> None:
    assert should_ignore_sync_path(
        task_root=tmp_path, path=tmp_path / relative, ignore_hidden_cache_paths=True,
    )


@pytest.mark.parametrize("relative", [
    "node_modules.md", "docs/node_modules-guide.md", "my_node_modules/index.js",
    "src/index.ts", "package.json", "package-lock.json", "dist/report.pdf",
])
def test_dependency_filter_preserves_project_files(tmp_path: Path, relative: str) -> None:
    assert not should_ignore_sync_path(
        task_root=tmp_path, path=tmp_path / relative, ignore_hidden_cache_paths=True,
    )


def test_dependency_filter_can_be_disabled_but_explicit_ignore_still_wins(tmp_path: Path) -> None:
    path = tmp_path / "project/node_modules/pkg/index.js"
    assert not should_ignore_sync_path(
        task_root=tmp_path, path=path, ignore_hidden_cache_paths=False,
    )
    assert should_ignore_sync_path(
        task_root=tmp_path, path=path, ignore_hidden_cache_paths=False,
        ignored_subpaths=["project/node_modules"],
    )


def test_local_scan_never_opens_ignored_dependency_directory(tmp_path: Path, monkeypatch) -> None:
    from src.services.sync_path_policy import iter_sync_local_files

    ignored = tmp_path / "project/node_modules"
    ignored.mkdir(parents=True)
    (ignored / "index.js").write_text("dependency", encoding="utf-8")
    document = tmp_path / "project/note.md"
    document.write_text("business document", encoding="utf-8")
    original_scandir = os.scandir

    def guarded_scandir(path):
        if Path(path) == ignored:
            pytest.fail("扫描进入了已排除的依赖目录")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", guarded_scandir)
    files = list(iter_sync_local_files(
        tmp_path,
        should_ignore=lambda path: should_ignore_sync_path(
            task_root=tmp_path, path=path, ignore_hidden_cache_paths=True,
        ),
    ))
    assert files == [document]
