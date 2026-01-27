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
