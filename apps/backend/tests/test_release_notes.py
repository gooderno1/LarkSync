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
        "v0.5.50",
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


def test_parse_development_log_and_render_detailed_sections() -> None:
    development_log = """
# DEVELOPMENT LOG

## v0.5.50-dev.2 (2026-02-18)

- 目标：
  - 修复 B
- 结果：
  - 调整同步器 B1
  - 修复同步器 B2
- 测试：
  - pytest b

## v0.5.50-dev.1 (2026-02-17)

- 目标：
  - 修复 A
- 结果：
  - 调整界面 A1
""".strip()
    sections = release_notes.parse_development_log(development_log)
    selected = release_notes.collect_devlog_sections_for_release(sections, "v0.5.50")
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
        items=[],
        dev_sections=selected,
    )

    assert [section.version for section in selected] == [
        "v0.5.50-dev.2",
        "v0.5.50-dev.1",
    ]
    assert "### 升级重点" in markdown
    assert "- `v0.5.50-dev.2`：调整同步器 B1" in markdown
    assert "#### v0.5.50-dev.1" in markdown
    assert "- 调整界面 A1" in markdown


def test_parse_development_log_supports_current_readability_headings() -> None:
    development_log = """
# DEVELOPMENT LOG

## v0.8.3-dev.4 (2026-07-22)

- 开发原因：
  - 旧页面不能展示全部任务。
- 实现方式：
  - 页面拆分为活动管理和问题中心。
- 当前结果：
  - 活动管理现在展示全部任务并分页查询事件。
  - 问题中心只渲染后端允许的动作。
- 验证方式：
  - 后端 583 项测试通过。
- 遗留问题：
  - 真实写动作仅在专用测试目录执行。
""".strip()

    sections = release_notes.parse_development_log(development_log)

    assert len(sections) == 1
    assert sections[0].goals == ["旧页面不能展示全部任务。"]
    assert sections[0].results == [
        "活动管理现在展示全部任务并分页查询事件。",
        "问题中心只渲染后端允许的动作。",
    ]
    assert sections[0].tests == ["后端 583 项测试通过。"]


def test_render_release_notes_appends_asset_checksums() -> None:
    markdown = release_notes.render_release_notes(
        target_version="v0.5.51",
        release_entry=release_notes.ChangelogEntry(
            date="2026-03-11",
            version="v0.5.51",
            message="release: v0.5.51",
        ),
        previous_release=release_notes.ChangelogEntry(
            date="2026-03-11",
            version="v0.5.50",
            message="release: v0.5.50",
        ),
        items=[
            release_notes.ChangelogEntry(
                date="2026-03-11",
                version="v0.5.51-dev.1",
                message="fix(update): add checksum assets",
            )
        ],
        asset_checksums=[
            ("LarkSync-Setup-v0.5.51.exe", "a" * 64),
        ],
    )

    assert "## 安装包校验" in markdown
    assert "| LarkSync-Setup-v0.5.51.exe | `" + ("a" * 64) + "` |" in markdown


def test_build_notes_fallback_when_no_target_release_marker(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        (
            "# CHANGELOG\n\n"
            "[2026-02-20] v0.5.50 fix(sync): carry change\n"
            "[2026-02-10] v0.5.49 release: v0.5.49\n"
        ),
        encoding="utf-8",
    )

    markdown = release_notes.build_notes(changelog_path, "v0.5.50")

    assert "# LarkSync v0.5.50" in markdown
    assert "### v0.5.50" in markdown
    assert "- [2026-02-20] fix(sync): carry change" in markdown


def test_build_notes_no_target_version_still_fallback_empty(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        "# CHANGELOG\n\n[2026-02-10] v0.5.49 release: v0.5.49\n",
        encoding="utf-8",
    )
    markdown = release_notes.build_notes(changelog_path, "v0.5.50")

    assert "# LarkSync v0.5.50" in markdown
    assert "未找到可归档的增量条目" in markdown


def test_build_notes_collects_asset_checksums(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        (
            "# CHANGELOG\n\n"
            "[2026-03-11] v0.5.51 release: v0.5.51\n"
            "[2026-03-11] v0.5.51-dev.1 fix(update): add checksum assets\n"
            "[2026-03-11] v0.5.50 release: v0.5.50\n"
        ),
        encoding="utf-8",
    )
    asset_path = tmp_path / "LarkSync-Setup-v0.5.51.exe"
    asset_path.write_bytes(b"binary")

    markdown = release_notes.build_notes(
        changelog_path,
        "v0.5.51",
        asset_paths=[asset_path],
    )

    assert "## 安装包校验" in markdown
    assert "LarkSync-Setup-v0.5.51.exe" in markdown
    assert release_notes.compute_sha256(asset_path) in markdown


def test_build_notes_prefers_development_log_for_stable_release(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        (
            "# CHANGELOG\n\n"
            "[2026-04-29] v0.6.2 release: v0.6.2\n"
            "[2026-04-29] v0.6.2-dev.2 fix(b): desc\n"
            "[2026-04-29] v0.6.2-dev.1 fix(a): desc\n"
            "[2026-04-28] v0.6.1 release: v0.6.1\n"
        ),
        encoding="utf-8",
    )
    development_log_path = tmp_path / "DEVELOPMENT_LOG.md"
    development_log_path.write_text(
        (
            "# DEVELOPMENT LOG\n\n"
            "## v0.6.2-dev.2 (2026-04-29)\n\n"
            "- 目标：\n"
            "  - 修复 B\n"
            "- 结果：\n"
            "  - 自动更新改走用户目录\n\n"
            "## v0.6.2-dev.1 (2026-04-29)\n\n"
            "- 目标：\n"
            "  - 修复 A\n"
            "- 结果：\n"
            "  - 删除墓碑执行前增加有效链接检查\n"
        ),
        encoding="utf-8",
    )

    markdown = release_notes.build_notes(
        changelog_path,
        "v0.6.2",
        development_log_path=development_log_path,
    )

    assert "### 升级重点" in markdown
    assert "#### v0.6.2-dev.2" in markdown
    assert "- 自动更新改走用户目录" in markdown


def test_build_notes_collects_devlog_sections_from_release_changelog_range(tmp_path: Path) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        (
            "# CHANGELOG\n\n"
            "[2026-05-11] v0.7.0 release: v0.7.0\n"
            "[2026-05-11] v0.6.21-dev.1 feat(log-center): event filters\n"
            "[2026-05-06] v0.6.20 release: v0.6.20\n"
        ),
        encoding="utf-8",
    )
    development_log_path = tmp_path / "DEVELOPMENT_LOG.md"
    development_log_path.write_text(
        (
            "# DEVELOPMENT LOG\n\n"
            "## v0.6.21-dev.1 (2026-05-11)\n\n"
            "- 目标：\n"
            "  - 增加事件筛选\n"
            "- 结果：\n"
            "  - 日志中心事件时间线可按上传、下载、删除分别查看\n"
        ),
        encoding="utf-8",
    )

    markdown = release_notes.build_notes(
        changelog_path,
        "v0.7.0",
        development_log_path=development_log_path,
    )

    assert "变更区间：v0.6.20 -> v0.7.0" in markdown
    assert "#### v0.6.21-dev.1" in markdown
    assert "- 日志中心事件时间线可按上传、下载、删除分别查看" in markdown
