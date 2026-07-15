from pathlib import Path

from src.core.config import CloudWritePolicy, ConfigManager, RuntimeProfile, SyncMode


def test_config_manager_env_override(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"sync_mode":"download_only"}', encoding="utf-8")

    db_path = tmp_path / "larksync.db"

    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_SYNC_MODE", "upload_only")
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(db_path))

    ConfigManager.reset()
    manager = ConfigManager.get()

    assert manager.config.sync_mode is SyncMode.upload_only
    assert manager.config.database_url.endswith(db_path.as_posix())


def test_config_manager_loads_isolated_runtime_profile(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "snapshot.db"))
    monkeypatch.setenv("LARKSYNC_RUNTIME_PROFILE", "snapshot_test")
    monkeypatch.setenv("LARKSYNC_CLOUD_WRITE_POLICY", "normal")
    monkeypatch.setenv("LARKSYNC_ALLOWED_CLOUD_ROOTS", "root-a, root-b")
    monkeypatch.setenv("LARKSYNC_FEISHU_RATE_PER_SECOND", "6.5")
    monkeypatch.setenv("LARKSYNC_FEISHU_RATE_BURST", "4")
    monkeypatch.setenv("LARKSYNC_CLOUD_AUDIT_LOG", str(tmp_path / "audit.jsonl"))

    ConfigManager.reset()
    config = ConfigManager.get().config

    assert config.runtime_profile is RuntimeProfile.snapshot_test
    assert config.cloud_write_policy is CloudWritePolicy.normal
    assert config.allowed_cloud_roots == ["root-a", "root-b"]
    assert config.effective_disable_scheduler is True
    assert config.effective_disable_watcher is True
    assert config.cloud_access_allowed is False
    assert config.effective_cloud_write_policy is CloudWritePolicy.deny
    assert config.feishu_rate_per_second == 6.5
    assert config.feishu_rate_burst == 4
    assert config.cloud_audit_log == str(tmp_path / "audit.jsonl")


def test_config_manager_defaults_include_required_docx_scopes(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "larksync.db"))

    ConfigManager.reset()
    manager = ConfigManager.get()

    assert manager.config.auth_scopes == [
        "drive:drive",
        "docx:document",
        "docx:document:readonly",
        "docx:document.block:convert",
        "drive:drive.metadata:readonly",
        "contact:contact.base:readonly",
    ]


def test_config_manager_migrates_legacy_docs_scope_to_docx_scopes(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            '{"auth_scopes":["drive:drive","docs:doc",'
            '"drive:drive.metadata:readonly","contact:contact.base:readonly"]}'
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "larksync.db"))

    ConfigManager.reset()
    manager = ConfigManager.get()

    assert "docs:doc" not in manager.config.auth_scopes
    assert manager.config.auth_scopes == [
        "drive:drive",
        "docx:document",
        "docx:document:readonly",
        "docx:document.block:convert",
        "drive:drive.metadata:readonly",
        "contact:contact.base:readonly",
    ]
