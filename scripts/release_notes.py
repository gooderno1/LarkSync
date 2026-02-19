from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ENTRY_RE = re.compile(
    r"^\[(?P<date>\d{4}-\d{2}-\d{2})\]\s+(?P<version>v?\d+\.\d+\.\d+(?:-dev\.\d+)?)\s+(?P<message>.+)$"
)


@dataclass(frozen=True)
class ChangelogEntry:
    date: str
    version: str
    message: str


def normalize_version(version: str) -> str:
    normalized = version.strip()
    if not normalized:
        return normalized
    return normalized if normalized.startswith("v") else f"v{normalized}"


def is_release_marker(entry: ChangelogEntry) -> bool:
    return "-dev." not in entry.version and entry.message.lower().startswith("release:")


def parse_changelog(text: str) -> list[ChangelogEntry]:
    entries: list[ChangelogEntry] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = ENTRY_RE.match(line)
        if not match:
            continue
        entries.append(
            ChangelogEntry(
                date=match.group("date"),
                version=normalize_version(match.group("version")),
                message=match.group("message").strip(),
            )
        )
    return entries


def collect_entries_for_release(
    entries: list[ChangelogEntry], target_version: str
) -> tuple[ChangelogEntry | None, ChangelogEntry | None, list[ChangelogEntry]]:
    target = normalize_version(target_version)
    release_idx: int | None = None
    for idx, entry in enumerate(entries):
        if entry.version == target and is_release_marker(entry):
            release_idx = idx
            break
    if release_idx is None:
        return None, None, []

    previous_release: ChangelogEntry | None = None
    tail: list[ChangelogEntry] = []
    for entry in entries[release_idx + 1 :]:
        if is_release_marker(entry):
            previous_release = entry
            break
        tail.append(entry)
    return entries[release_idx], previous_release, tail


def _iter_grouped(entries: Iterable[ChangelogEntry]) -> list[tuple[str, list[ChangelogEntry]]]:
    groups: list[tuple[str, list[ChangelogEntry]]] = []
    current_version = ""
    current_entries: list[ChangelogEntry] = []
    for entry in entries:
        if entry.version != current_version:
            if current_entries:
                groups.append((current_version, current_entries))
            current_version = entry.version
            current_entries = [entry]
        else:
            current_entries.append(entry)
    if current_entries:
        groups.append((current_version, current_entries))
    return groups


def render_release_notes(
    target_version: str,
    release_entry: ChangelogEntry | None,
    previous_release: ChangelogEntry | None,
    items: list[ChangelogEntry],
) -> str:
    normalized_target = normalize_version(target_version)
    lines: list[str] = [f"# LarkSync {normalized_target}", ""]

    if release_entry is not None:
        lines.append(f"- 发布日期：{release_entry.date}")
    if previous_release is not None:
        lines.append(f"- 变更区间：{previous_release.version} -> {normalized_target}")
    else:
        lines.append("- 变更区间：项目起始版本 -> 当前版本")
    lines.append("")
    lines.append("## 本次更新明细")

    filtered = [entry for entry in items if not is_release_marker(entry)]
    if not filtered:
        lines.append("- 未找到可归档的增量条目，请查看 `CHANGELOG.md`。")
        return "\n".join(lines).rstrip() + "\n"

    lines.append("")
    for version, group in _iter_grouped(filtered):
        lines.append(f"### {version}")
        for entry in group:
            lines.append(f"- [{entry.date}] {entry.message}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_notes(changelog_path: Path, target_version: str) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    entries = parse_changelog(text)
    release_entry, previous_release, items = collect_entries_for_release(entries, target_version)
    return render_release_notes(target_version, release_entry, previous_release, items)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GitHub Release notes from CHANGELOG")
    parser.add_argument("--version", default=os.getenv("GITHUB_REF_NAME", ""), help="target release version/tag")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="path to CHANGELOG file")
    parser.add_argument("--output", default="", help="output markdown file path")
    args = parser.parse_args()

    version = normalize_version(args.version)
    if not version:
        parser.error("--version is required (or provide GITHUB_REF_NAME)")
    changelog_path = Path(args.changelog).resolve()
    if not changelog_path.exists():
        parser.error(f"CHANGELOG not found: {changelog_path}")

    content = build_notes(changelog_path, version)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
