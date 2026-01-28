from pathlib import Path

from fastapi.testclient import TestClient

from src.core.config import ConfigManager
from src.main import app


def test_login_returns_400_when_config_missing(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LARKSYNC_CONFIG", str(config_path))
    ConfigManager.reset()

    client = TestClient(app)
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 400
