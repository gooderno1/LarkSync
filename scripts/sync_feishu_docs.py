#!/usr/bin/env python3
"""Sync latest Feishu developer handbook archives into docs/feishu."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

SOURCE_URL = "https://project.feishu.cn/b/helpcenter/1p8d7djs/qcw96ljx"
DEFAULT_TARGET_DIR = Path("docs/feishu")
MANIFEST_FILE = "_manifest.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LarkSyncDocSync/1.0"

ZIP_ENTRY_PATTERN = re.compile(
    r'"src":"(?P<src>https:\\u002F\\u002F[^"]+)".{0,600}?"filename":"(?P<filename>[^"]+?\.zip)"',
    re.DOTALL,
)


@dataclass(frozen=True)
class ZipEntry:
    filename: str
    url: str


def fetch_html(url: str) -> str:
    request = Request(url=url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def decode_source_url(raw_url: str) -> str:
    return (
        raw_url.replace("\\u002F", "/")
        .replace("\\/", "/")
        .replace("\\u003A", ":")
        .replace("\\u003F", "?")
        .replace("\\u003D", "=")
        .replace("\\u0026", "&")
    )


def extract_zip_entries(html: str) -> list[ZipEntry]:
    seen: set[str] = set()
    entries: list[ZipEntry] = []
    for match in ZIP_ENTRY_PATTERN.finditer(html):
        filename = match.group("filename").strip()
        if filename in seen:
            continue
        url = decode_source_url(match.group("src"))
        seen.add(filename)
        entries.append(ZipEntry(filename=filename, url=url))
    return entries


def download_file(url: str, output_path: Path) -> None:
    request = Request(url=url, headers={"User-Agent": USER_AGENT, "Referer": SOURCE_URL})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    output_path.write_bytes(data)


def write_manifest(target_dir: Path, entries: list[ZipEntry], downloaded: list[str]) -> None:
    manifest = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": SOURCE_URL,
        "archives": [
            {
                "filename": entry.filename,
                "url": entry.url,
                "downloaded_this_run": entry.filename in downloaded,
                "present_locally": (target_dir / entry.filename).exists(),
            }
            for entry in entries
        ],
    }
    (target_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sync_docs(target_dir: Path, force: bool) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)
    html = fetch_html(SOURCE_URL)
    entries = extract_zip_entries(html)
    if not entries:
        print("未在页面中解析到 zip 文档，请检查页面结构是否变化。")
        return 2

    downloaded: list[str] = []
    for entry in entries:
        output_path = target_dir / entry.filename
        if output_path.exists() and not force:
            print(f"[skip] {entry.filename}")
            continue
        print(f"[download] {entry.filename}")
        download_file(entry.url, output_path)
        downloaded.append(entry.filename)

    write_manifest(target_dir, entries, downloaded)
    print(
        f"完成：共 {len(entries)} 个文档，新增/覆盖 {len(downloaded)} 个。"
        f" 清单已写入 {target_dir / MANIFEST_FILE}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Feishu developer docs archives.")
    parser.add_argument(
        "--target-dir",
        default=str(DEFAULT_TARGET_DIR),
        help="Output directory for downloaded archives.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if archive already exists locally.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return sync_docs(Path(args.target_dir), force=args.force)
    except URLError as exc:
        print(f"下载失败：{exc}")
        return 1
    except Exception as exc:  # pragma: no cover - safety net for CLI use
        print(f"执行失败：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
