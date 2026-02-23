from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = (
    ROOT
    / "integrations"
    / "openclaw"
    / "skills"
    / "larksync_feishu_local_cache"
    / "scripts"
    / "larksync_skill_helper.py"
)

spec = importlib.util.spec_from_file_location("larksync_skill_helper", HELPER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"无法加载脚本模块: {HELPER_PATH}")
helper = importlib.util.module_from_spec(spec)
sys.modules["larksync_skill_helper"] = helper
spec.loader.exec_module(helper)


def test_validate_hhmm() -> None:
    assert helper._validate_hhmm("01:00") is True
    assert helper._validate_hhmm("23:59") is True
    assert helper._validate_hhmm("24:00") is False
    assert helper._validate_hhmm("aa:bb") is False


def test_build_download_config_payload_days() -> None:
    payload = helper.build_download_config_payload(1, "days", "02:30")
    assert payload["download_interval_value"] == 1.0
    assert payload["download_interval_unit"] == "days"
    assert payload["download_daily_time"] == "02:30"


def test_build_download_config_payload_invalid_daily_time() -> None:
    with pytest.raises(ValueError):
        helper.build_download_config_payload(1, "days", "2:70")


def test_infer_md_sync_mode() -> None:
    assert helper.infer_md_sync_mode("download_only") == "download_only"
    assert helper.infer_md_sync_mode("bidirectional") == "enhanced"


def test_build_task_payload() -> None:
    payload = helper.build_task_payload(
        name="Demo",
        local_path=r"C:\data\docs",
        cloud_folder_token="fld_xxx",
        sync_mode="download_only",
    )
    assert payload["name"] == "Demo"
    assert payload["local_path"].lower().endswith(r"c:\data\docs".lower())
    assert payload["cloud_folder_token"] == "fld_xxx"
    assert payload["sync_mode"] == "download_only"
    assert payload["md_sync_mode"] == "download_only"


def test_build_task_payload_invalid_mode() -> None:
    with pytest.raises(ValueError):
        helper.build_task_payload(
            name="Demo",
            local_path=r"C:\data\docs",
            cloud_folder_token="fld_xxx",
            sync_mode="invalid",
        )


def test_validate_base_url_localhost_default() -> None:
    assert helper.validate_base_url("http://localhost:8000") == "http://localhost:8000"
    assert helper.validate_base_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert helper.validate_base_url("http://[::1]:8000/") == "http://[::1]:8000"


def test_validate_base_url_reject_remote_by_default() -> None:
    with pytest.raises(ValueError, match="localhost"):
        helper.validate_base_url("https://example.com")


def test_validate_base_url_allow_remote_with_opt_in() -> None:
    assert helper.validate_base_url("https://example.com", allow_remote=True) == "https://example.com"


def test_validate_base_url_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="http 或 https"):
        helper.validate_base_url("ftp://localhost:8000")
