from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "scripts" / "sync_feishu_docs.py"
SPEC = importlib.util.spec_from_file_location("sync_feishu_docs", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
sync_feishu_docs = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync_feishu_docs
SPEC.loader.exec_module(sync_feishu_docs)


def test_extract_zip_entries_from_legacy_pair() -> None:
    html = (
        '"src":"https:\\u002F\\u002Fexample.com\\u002Fdocs\\u002Fguide.zip",'
        '"filename":"guide.zip"'
    )
    entries = sync_feishu_docs.extract_zip_entries(html)
    assert len(entries) == 1
    assert entries[0].filename == "guide.zip"
    assert entries[0].url == "https://example.com/docs/guide.zip"


def test_extract_zip_entries_from_direct_url() -> None:
    html = '<a href="https://cdn.example.com/releases/docs%20bundle.zip?download=1">zip</a>'
    entries = sync_feishu_docs.extract_zip_entries(html)
    assert len(entries) == 1
    assert entries[0].filename == "docs bundle.zip"
    assert entries[0].url.startswith("https://cdn.example.com/releases/docs%20bundle.zip")


def test_sync_docs_no_zip_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sync_feishu_docs, "fetch_html", lambda _url: "<html></html>")
    called = {"download": 0}

    def fake_download(*_args, **_kwargs):
        called["download"] += 1

    monkeypatch.setattr(sync_feishu_docs, "download_file", fake_download)
    code = sync_feishu_docs.sync_docs(tmp_path, force=False)
    manifest = json.loads((tmp_path / "_manifest.json").read_text(encoding="utf-8"))

    assert code == 0
    assert called["download"] == 0
    assert manifest["status"] == "no_zip_found"
    assert manifest["archives"] == []
