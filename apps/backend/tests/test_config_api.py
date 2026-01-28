import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.core.config import ConfigManager
from src.main import app


def test_get_config_masks_secret(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "auth_authorize_url": "https://example.com/auth",
                "auth_token_url": "https://example.com/token",
                "auth_client_id": "app-id",
                "auth_client_secret": "secret",
                "auth_redirect_uri": "http://localhost/callback",
                "auth_scopes": ["a", "b"],
            }
        ),
        encoding="utf-8",
    )
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'db.sqlite').as_posix()}"
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_DATABASE_URL", db_url)
    ConfigManager.reset()

    client = TestClient(app)
    response = client.get("/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_client_secret"] == ""
    assert payload["auth_client_id"] == "app-id"


def test_update_config_persists(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'db.sqlite').as_posix()}"
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    monkeypatch.setenv("LARKSYNC_DATABASE_URL", db_url)
    ConfigManager.reset()

    client = TestClient(app)
    response = client.put(
        "/config",
        json={
            "auth_authorize_url": "https://auth.example.com",
            "auth_token_url": "https://token.example.com",
            "auth_client_id": "new-id",
            "auth_client_secret": "new-secret",
            "auth_redirect_uri": "http://localhost:8000/auth/callback",
            "auth_scopes": ["drive:drive"],
            "sync_mode": "upload_only",
            "token_store": "keyring",
        },
    )
    assert response.status_code == 200

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["auth_client_id"] == "new-id"
    assert persisted["auth_client_secret"] == "new-secret"
    assert persisted["sync_mode"] == "upload_only"
