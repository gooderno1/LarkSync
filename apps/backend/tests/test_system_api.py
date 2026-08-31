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


def test_shutdown_schedules_background(monkeypatch) -> None:
    called = {}

    def fake_schedule(app_instance) -> None:
        called["app"] = app_instance

    monkeypatch.setattr(system, "_schedule_shutdown", fake_schedule)
    client = TestClient(app)
    response = client.post("/system/shutdown")
    assert response.status_code == 200
    assert response.json()["status"] == "shutting_down"
    assert called.get("app") is app


def test_autostart_status_reports_real_platform_state(monkeypatch) -> None:
    monkeypatch.setattr(system, "_autostart_platform", lambda: "windows")
    monkeypatch.setattr(system, "_autostart_supported", lambda: True)
    monkeypatch.setattr(system, "_autostart_enabled", lambda: True)

    client = TestClient(app)
    response = client.get("/system/autostart")

    assert response.status_code == 200
    assert response.json() == {
        "supported": True,
        "enabled": True,
        "platform": "windows",
    }


def test_autostart_update_returns_verified_state(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(system, "_autostart_platform", lambda: "macos")
    monkeypatch.setattr(system, "_autostart_supported", lambda: True)
    monkeypatch.setattr(
        system,
        "_set_autostart_enabled",
        lambda enabled: calls.append(enabled) or True,
    )
    monkeypatch.setattr(system, "_autostart_enabled", lambda: True)

    client = TestClient(app)
    response = client.put("/system/autostart", json={"enabled": True})

    assert response.status_code == 200
    assert response.json() == {
        "supported": True,
        "enabled": True,
        "platform": "macos",
    }
    assert calls == [True]


def test_autostart_update_rejects_unsupported_platform(monkeypatch) -> None:
    monkeypatch.setattr(system, "_autostart_platform", lambda: "unsupported")
    monkeypatch.setattr(system, "_autostart_supported", lambda: False)

    client = TestClient(app)
    response = client.put("/system/autostart", json={"enabled": True})

    assert response.status_code == 400
    assert response.json()["detail"] == "当前平台不支持开机自启动"
