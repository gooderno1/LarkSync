from fastapi.testclient import TestClient

from src.main import app


def test_login_returns_400_when_config_missing() -> None:
    client = TestClient(app)
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 400
