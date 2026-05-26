from pathlib import Path

from src.core.config import ConfigManager, SyncMode


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
