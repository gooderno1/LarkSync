#!/usr/bin/env python3
"""Sync latest Feishu developer handbook archives into docs/feishu."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlparse
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
DIRECT_ZIP_URL_PATTERN = re.compile(r'https[^"\'<>\s]+', re.IGNORECASE)


@dataclass(frozen=True)
class ZipEntry:
    filename: str
    url: str


def fetch_html(url: str) -> str:
    request = Request(url=url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def decode_source_url(raw_url: str) -> str:
    decoded = (
        raw_url.replace("\\u002F", "/")
        .replace("\\/", "/")
        .replace("\\u003A", ":")
        .replace("\\u003F", "?")
        .replace("\\u003D", "=")
        .replace("\\u0026", "&")
        .replace("\\u0025", "%")
    )
    return unescape(decoded)


def _is_zip_url(url: str) -> bool:
    parsed = urlparse(url)
    file_name = unquote(Path(parsed.path).name)
    return file_name.lower().endswith(".zip")


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    file_name = unquote(Path(parsed.path).name)
    if file_name:
        return file_name
    return "feishu-docs.zip"


def extract_zip_entries(html: str) -> list[ZipEntry]:
    seen: set[tuple[str, str]] = set()
    entries: list[ZipEntry] = []

    # 兼容旧页面结构：src + filename 成对出现
    for match in ZIP_ENTRY_PATTERN.finditer(html):
        filename = match.group("filename").strip()
        url = decode_source_url(match.group("src"))
        key = (filename, url)
        if key in seen:
            continue
        seen.add(key)
        entries.append(ZipEntry(filename=filename, url=url))

    # 兼容新页面结构：直接出现 zip 链接（可能在 JSON、href、script 文本中）
    for raw in DIRECT_ZIP_URL_PATTERN.findall(html):
        url = decode_source_url(raw)
        if not _is_zip_url(url):
            continue
        filename = _filename_from_url(url)
        key = (filename, url)
        if key in seen:
            continue
        seen.add(key)
        entries.append(ZipEntry(filename=filename, url=url))

    return entries


def download_file(url: str, output_path: Path) -> None:
    request = Request(url=url, headers={"User-Agent": USER_AGENT, "Referer": SOURCE_URL})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    output_path.write_bytes(data)


def write_manifest(
    target_dir: Path,
    entries: list[ZipEntry],
    downloaded: list[str],
    status: str = "ok",
    message: str | None = None,
) -> None:
    manifest = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": SOURCE_URL,
        "status": status,
        "message": message,
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
        message = (
            "页面中未发现 zip 文档链接，本次仅更新清单。"
            " 若预期应有 zip，请检查入口页面是否改版。"
        )
        write_manifest(
            target_dir,
            entries=[],
            downloaded=[],
            status="no_zip_found",
            message=message,
        )
        print(message)
        return 0

    downloaded: list[str] = []
    for entry in entries:
        output_path = target_dir / entry.filename
        if output_path.exists() and not force:
            print(f"[skip] {entry.filename}")
            continue
        print(f"[download] {entry.filename}")
        download_file(entry.url, output_path)
        downloaded.append(entry.filename)

    write_manifest(target_dir, entries, downloaded, status="ok", message=None)
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
