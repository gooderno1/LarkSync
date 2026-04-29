from __future__ import annotations

import argparse
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ENTRY_RE = re.compile(
    r"^\[(?P<date>\d{4}-\d{2}-\d{2})\]\s+(?P<version>v?\d+\.\d+\.\d+(?:-dev\.\d+)?)\s+(?P<message>.+)$"
)
DEV_LOG_HEADING_RE = re.compile(
    r"^##\s+(?P<version>v?\d+\.\d+\.\d+(?:-dev\.\d+)?|v?\d+\.\d+\.\d+\s+release)\s+\((?P<date>\d{4}-\d{2}-\d{2})\)$"
)


@dataclass(frozen=True)
class ChangelogEntry:
    date: str
    version: str
    message: str


@dataclass(frozen=True)
class DevelopmentLogSection:
    date: str
    version: str
    goals: list[str]
    results: list[str]
    tests: list[str]
    raw_title: str


def normalize_version(version: str) -> str:
    normalized = version.strip()
    if not normalized:
        return normalized
    return normalized if normalized.startswith("v") else f"v{normalized}"


def normalize_devlog_version(version: str) -> str:
    normalized = version.strip()
    if normalized.endswith(" release"):
        normalized = normalized[: -len(" release")].strip()
    return normalize_version(normalized)


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


def parse_development_log(text: str) -> list[DevelopmentLogSection]:
    sections: list[DevelopmentLogSection] = []
    current_title = ""
    current_date = ""
    current_version = ""
    goals: list[str] = []
    results: list[str] = []
    tests: list[str] = []
    active_bucket: list[str] | None = None

    def flush() -> None:
        nonlocal current_title, current_date, current_version, goals, results, tests, active_bucket
        if not current_version:
            return
        sections.append(
            DevelopmentLogSection(
                date=current_date,
                version=current_version,
                goals=list(goals),
                results=list(results),
                tests=list(tests),
                raw_title=current_title,
            )
        )
        current_title = ""
        current_date = ""
        current_version = ""
        goals = []
        results = []
        tests = []
        active_bucket = None

    for raw in text.splitlines():
        line = raw.rstrip()
        heading_match = DEV_LOG_HEADING_RE.match(line.strip())
        if heading_match:
            flush()
            current_title = line.strip()
            current_date = heading_match.group("date")
            current_version = normalize_devlog_version(heading_match.group("version"))
            continue
        if not current_version:
            continue
        stripped = line.strip()
        if stripped == "- 目标：":
            active_bucket = goals
            continue
        if stripped == "- 结果：":
            active_bucket = results
            continue
        if stripped == "- 测试：":
            active_bucket = tests
            continue
        if active_bucket is not None and stripped.startswith("- "):
            active_bucket.append(stripped[2:].strip())

    flush()
    return sections


def collect_entries_for_release(
    entries: list[ChangelogEntry], target_version: str
) -> tuple[ChangelogEntry | None, ChangelogEntry | None, list[ChangelogEntry]]:
    target = normalize_version(target_version)
    release_idx: int | None = None
    fallback_idx: int | None = None
    for idx, entry in enumerate(entries):
        if entry.version != target:
            continue
        if fallback_idx is None:
            fallback_idx = idx
        if is_release_marker(entry):
            release_idx = idx
            break
    if release_idx is None:
        # 兼容：若缺失 release: 标记，则使用该版本第一条记录作为锚点。
        if fallback_idx is None:
            return None, None, []
        release_idx = fallback_idx

    previous_release: ChangelogEntry | None = None
    tail: list[ChangelogEntry] = []
    for entry in entries[release_idx + 1 :]:
        if "-dev." not in entry.version:
            previous_release = entry
            break
        tail.append(entry)

    # 包含锚点本身（若是 release: 行，会在渲染时被过滤掉）。
    items = [entries[release_idx], *tail]
    return entries[release_idx], previous_release, items


def collect_devlog_sections_for_release(
    sections: list[DevelopmentLogSection], target_version: str
) -> list[DevelopmentLogSection]:
    target = normalize_version(target_version)
    prefix = f"{target}-dev."
    return [section for section in sections if section.version.startswith(prefix)]


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
    dev_sections: list[DevelopmentLogSection] | None = None,
    asset_checksums: list[tuple[str, str]] | None = None,
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

    if dev_sections:
        lines.append("")
        lines.append("### 升级重点")
        for section in dev_sections:
            highlight = section.results[0] if section.results else f"{section.version} 包含内部改动，请查看详细变更。"
            lines.append(f"- `{section.version}`：{highlight}")
        lines.append("")
        lines.append("### 详细变更")
        lines.append("")
        for section in dev_sections:
            lines.append(f"#### {section.version}")
            if section.results:
                for item in section.results:
                    lines.append(f"- {item}")
            else:
                lines.append("- 本版本未在 `DEVELOPMENT_LOG.md` 中记录详细结果。")
            lines.append("")
        if asset_checksums:
            lines.append("## 安装包校验")
            lines.append("")
            lines.append("| asset | sha256 |")
            lines.append("| --- | --- |")
            for asset_name, digest in asset_checksums:
                lines.append(f"| {asset_name} | `{digest}` |")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

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

    if asset_checksums:
        lines.append("## 安装包校验")
        lines.append("")
        lines.append("| asset | sha256 |")
        lines.append("| --- | --- |")
        for asset_name, digest in asset_checksums:
            lines.append(f"| {asset_name} | `{digest}` |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_asset_checksums(asset_paths: Iterable[Path]) -> list[tuple[str, str]]:
    checksums: list[tuple[str, str]] = []
    for path in asset_paths:
        resolved = Path(path)
        if not resolved.is_file():
            continue
        checksums.append((resolved.name, compute_sha256(resolved)))
    return checksums


def build_notes(
    changelog_path: Path,
    target_version: str,
    development_log_path: Path | None = None,
    asset_paths: Iterable[Path] | None = None,
) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    entries = parse_changelog(text)
    release_entry, previous_release, items = collect_entries_for_release(entries, target_version)
    dev_sections: list[DevelopmentLogSection] | None = None
    if development_log_path and development_log_path.exists():
        dev_text = development_log_path.read_text(encoding="utf-8")
        dev_sections = collect_devlog_sections_for_release(
            parse_development_log(dev_text),
            target_version,
        )
    checksums = collect_asset_checksums(asset_paths or [])
    return render_release_notes(
        target_version,
        release_entry,
        previous_release,
        items,
        dev_sections=dev_sections,
        asset_checksums=checksums,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GitHub Release notes from CHANGELOG")
    parser.add_argument("--version", default=os.getenv("GITHUB_REF_NAME", ""), help="target release version/tag")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="path to CHANGELOG file")
    parser.add_argument(
        "--development-log",
        default="DEVELOPMENT_LOG.md",
        help="path to DEVELOPMENT_LOG file",
    )
    parser.add_argument("--output", default="", help="output markdown file path")
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        help="asset file path or glob pattern; can be specified multiple times",
    )
    args = parser.parse_args()

    version = normalize_version(args.version)
    if not version:
        parser.error("--version is required (or provide GITHUB_REF_NAME)")
    changelog_path = Path(args.changelog).resolve()
    if not changelog_path.exists():
        parser.error(f"CHANGELOG not found: {changelog_path}")
    development_log_path = Path(args.development_log).resolve()

    asset_paths: list[Path] = []
    for raw in args.asset:
        matched = sorted(Path().glob(raw))
        if matched:
            asset_paths.extend(path.resolve() for path in matched if path.is_file())
            continue
        candidate = Path(raw).resolve()
        if candidate.is_file():
            asset_paths.append(candidate)

    content = build_notes(
        changelog_path,
        version,
        development_log_path=development_log_path,
        asset_paths=asset_paths,
    )
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
