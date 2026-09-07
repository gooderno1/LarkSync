from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import accounts
from src.core import macos_keychain


def test_status_never_reads_credentials(monkeypatch):
    monkeypatch.setattr(macos_keychain, "enabled", lambda: False)
    app = FastAPI()
    app.include_router(accounts.router)
    response = TestClient(app).get("/auth/keychain/status")
    assert response.status_code == 200
    assert response.json() == {"supported": False, "blocked": False, "retrying": False, "message": None}


def test_explicit_retry_calls_service_and_reloads_runtime(monkeypatch):
    retry = AsyncMock()
    reload = AsyncMock()
    monkeypatch.setattr(macos_keychain, "enabled", lambda: True)
    monkeypatch.setattr(accounts.account_service, "retry_keychain_access", retry)
    monkeypatch.setattr(accounts.account_runtime_registry, "reload", reload)
    app = FastAPI()
    app.include_router(accounts.router)
    assert TestClient(app).post("/auth/keychain/retry").status_code == 200
    retry.assert_awaited_once()
    reload.assert_awaited_once()


def test_credential_failure_is_actionable_and_redacted(monkeypatch):
    from src import main
    from src.core.security import CredentialStorageError

    async def fail():
        raise CredentialStorageError("系统安全凭据读取失败")

    monkeypatch.setattr(accounts.account_service, "list_account_summaries", fail)
    response = TestClient(main.create_app()).get("/accounts/summary")
    assert response.status_code == 503
    assert response.json()["code"] == "credential_storage_unavailable"
    assert "系统安全凭据" in response.json()["detail"]
