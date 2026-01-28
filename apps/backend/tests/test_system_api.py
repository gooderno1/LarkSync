from fastapi.testclient import TestClient

from src.api import system
from src.main import app


def test_select_folder_success(monkeypatch) -> None:
    monkeypatch.setattr(system, "_select_folder", lambda: "C:/Docs")
    client = TestClient(app)
    response = client.post("/system/select-folder")
    assert response.status_code == 200
    assert response.json()["path"] == "C:/Docs"


def test_select_folder_cancel(monkeypatch) -> None:
    monkeypatch.setattr(system, "_select_folder", lambda: None)
    client = TestClient(app)
    response = client.post("/system/select-folder")
    assert response.status_code == 400
