from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts import release_notes  # noqa: E402


def test_collect_entries_between_stable_releases() -> None:
    changelog = """
# CHANGELOG

[2026-02-20] v0.5.50 release: v0.5.50
[2026-02-19] v0.5.50-dev.3 fix(sync): c
[2026-02-18] v0.5.50-dev.2 feat(sync): b
[2026-02-17] v0.5.50-dev.1 feat(ui): a
[2026-02-10] v0.5.49 release: v0.5.49
[2026-02-09] v0.5.49-dev.1 feat(old): z
""".strip()
    entries = release_notes.parse_changelog(changelog)

    release_entry, previous_release, items = release_notes.collect_entries_for_release(
        entries, "v0.5.50"
    )

    assert release_entry is not None
    assert release_entry.version == "v0.5.50"
    assert previous_release is not None
    assert previous_release.version == "v0.5.49"
    assert [entry.version for entry in items] == [
        "v0.5.50-dev.3",
        "v0.5.50-dev.2",
        "v0.5.50-dev.1",
    ]


def test_render_release_notes_groups_multiple_versions() -> None:
    items = [
        release_notes.ChangelogEntry(
            date="2026-02-19",
            version="v0.5.50-dev.3",
            message="fix(sync): c",
        ),
        release_notes.ChangelogEntry(
            date="2026-02-18",
            version="v0.5.50-dev.2",
            message="feat(sync): b",
        ),
        release_notes.ChangelogEntry(
            date="2026-02-17",
            version="v0.5.50-dev.2",
            message="fix(ui): b2",
        ),
    ]
    markdown = release_notes.render_release_notes(
        target_version="v0.5.50",
        release_entry=release_notes.ChangelogEntry(
            date="2026-02-20",
            version="v0.5.50",
            message="release: v0.5.50",
        ),
        previous_release=release_notes.ChangelogEntry(
            date="2026-02-10",
            version="v0.5.49",
            message="release: v0.5.49",
        ),
        items=items,
    )

    assert "# LarkSync v0.5.50" in markdown
    assert "变更区间：v0.5.49 -> v0.5.50" in markdown
    assert "### v0.5.50-dev.3" in markdown
    assert "### v0.5.50-dev.2" in markdown
    assert "- [2026-02-17] fix(ui): b2" in markdown


def test_build_notes_fallback_when_no_target_release_marker(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        "# CHANGELOG\n\n[2026-02-10] v0.5.49 release: v0.5.49\n",
        encoding="utf-8",
    )

    markdown = release_notes.build_notes(changelog_path, "v0.5.50")

    assert "# LarkSync v0.5.50" in markdown
    assert "未找到可归档的增量条目" in markdown
