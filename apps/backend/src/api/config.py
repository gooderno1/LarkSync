from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config import AppConfig, ConfigManager, SyncMode


class ConfigResponse(BaseModel):
    auth_authorize_url: str = ""
    auth_token_url: str = ""
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_redirect_uri: str = ""
    auth_scopes: list[str] = Field(default_factory=list)
    sync_mode: SyncMode = SyncMode.bidirectional
    token_store: str = "keyring"

    @classmethod
    def from_config(cls, config: AppConfig, mask_secret: bool = True) -> "ConfigResponse":
        return cls(
            auth_authorize_url=config.auth_authorize_url,
            auth_token_url=config.auth_token_url,
            auth_client_id=config.auth_client_id,
            auth_client_secret="" if mask_secret else config.auth_client_secret,
            auth_redirect_uri=config.auth_redirect_uri,
            auth_scopes=list(config.auth_scopes or []),
            sync_mode=config.sync_mode,
            token_store=config.token_store,
        )


class ConfigUpdateRequest(BaseModel):
    auth_authorize_url: str | None = None
    auth_token_url: str | None = None
    auth_client_id: str | None = None
    auth_client_secret: str | None = None
    auth_redirect_uri: str | None = None
    auth_scopes: list[str] | None = None
    sync_mode: SyncMode | None = None
    token_store: str | None = None


router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    manager = ConfigManager.get()
    return ConfigResponse.from_config(manager.config, mask_secret=True)


@router.put("", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdateRequest) -> ConfigResponse:
    manager = ConfigManager.get()
    data = _read_config_file(manager.config_path)

    _apply_str(data, "auth_authorize_url", payload.auth_authorize_url)
    _apply_str(data, "auth_token_url", payload.auth_token_url)
    _apply_str(data, "auth_client_id", payload.auth_client_id)
    _apply_str(data, "auth_redirect_uri", payload.auth_redirect_uri)

    if payload.auth_client_secret is not None and payload.auth_client_secret.strip():
        data["auth_client_secret"] = payload.auth_client_secret.strip()

    if payload.auth_scopes is not None:
        data["auth_scopes"] = [scope for scope in payload.auth_scopes if scope]

    if payload.sync_mode is not None:
        data["sync_mode"] = payload.sync_mode.value

    if payload.token_store is not None and payload.token_store.strip():
        data["token_store"] = payload.token_store.strip()

    config = manager.save_config(data)
    return ConfigResponse.from_config(config, mask_secret=True)


def _read_config_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _apply_str(data: dict[str, object], key: str, value: str | None) -> None:
    if value is None:
        return
    cleaned = value.strip()
    if cleaned:
        data[key] = cleaned

