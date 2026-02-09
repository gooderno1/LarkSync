from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.config import AppConfig, ConfigManager, SyncIntervalUnit, SyncMode


class ConfigResponse(BaseModel):
    auth_authorize_url: str = "https://open.feishu.cn/open-apis/authen/v1/authorize"
    auth_token_url: str = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_redirect_uri: str = ""
    auth_scopes: list[str] = Field(default_factory=list)
    sync_mode: SyncMode = SyncMode.bidirectional
    token_store: str = "keyring"
    upload_interval_value: float = 2.0
    upload_interval_unit: SyncIntervalUnit = SyncIntervalUnit.seconds
    upload_daily_time: str = "01:00"
    download_interval_value: float = 1.0
    download_interval_unit: SyncIntervalUnit = SyncIntervalUnit.days
    download_daily_time: str = "01:00"
    sync_log_retention_days: int = 0
    sync_log_warn_size_mb: int = 200
    system_log_retention_days: int = 1
    auto_update_enabled: bool = False
    update_check_interval_hours: int = 24
    last_update_check: float = 0.0
    allow_dev_to_stable: bool = False

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
            upload_interval_value=config.upload_interval_value,
            upload_interval_unit=config.upload_interval_unit,
            upload_daily_time=config.upload_daily_time,
            download_interval_value=config.download_interval_value,
            download_interval_unit=config.download_interval_unit,
            download_daily_time=config.download_daily_time,
            sync_log_retention_days=config.sync_log_retention_days,
            sync_log_warn_size_mb=config.sync_log_warn_size_mb,
            system_log_retention_days=config.system_log_retention_days,
            auto_update_enabled=config.auto_update_enabled,
            update_check_interval_hours=config.update_check_interval_hours,
            last_update_check=config.last_update_check,
            allow_dev_to_stable=config.allow_dev_to_stable,
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
    upload_interval_value: float | None = None
    upload_interval_unit: SyncIntervalUnit | None = None
    upload_daily_time: str | None = None
    download_interval_value: float | None = None
    download_interval_unit: SyncIntervalUnit | None = None
    download_daily_time: str | None = None
    sync_log_retention_days: int | None = None
    sync_log_warn_size_mb: int | None = None
    system_log_retention_days: int | None = None
    auto_update_enabled: bool | None = None
    update_check_interval_hours: int | None = None
    allow_dev_to_stable: bool | None = None


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

    if payload.upload_interval_value is not None and payload.upload_interval_value > 0:
        data["upload_interval_value"] = payload.upload_interval_value

    if payload.upload_interval_unit is not None:
        data["upload_interval_unit"] = payload.upload_interval_unit.value

    if payload.upload_daily_time is not None:
        cleaned = payload.upload_daily_time.strip()
        if cleaned and _is_time_value(cleaned):
            data["upload_daily_time"] = cleaned

    if payload.download_interval_value is not None and payload.download_interval_value > 0:
        data["download_interval_value"] = payload.download_interval_value

    if payload.download_interval_unit is not None:
        data["download_interval_unit"] = payload.download_interval_unit.value

    if payload.download_daily_time is not None:
        cleaned = payload.download_daily_time.strip()
        if cleaned:
            if _is_time_value(cleaned):
                data["download_daily_time"] = cleaned

    if payload.sync_log_retention_days is not None and payload.sync_log_retention_days >= 0:
        data["sync_log_retention_days"] = payload.sync_log_retention_days

    if payload.sync_log_warn_size_mb is not None and payload.sync_log_warn_size_mb >= 0:
        data["sync_log_warn_size_mb"] = payload.sync_log_warn_size_mb

    if payload.system_log_retention_days is not None and payload.system_log_retention_days > 0:
        data["system_log_retention_days"] = payload.system_log_retention_days

    if payload.auto_update_enabled is not None:
        data["auto_update_enabled"] = bool(payload.auto_update_enabled)

    if payload.update_check_interval_hours is not None and payload.update_check_interval_hours > 0:
        data["update_check_interval_hours"] = payload.update_check_interval_hours

    if payload.allow_dev_to_stable is not None:
        data["allow_dev_to_stable"] = bool(payload.allow_dev_to_stable)

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


def _is_time_value(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False
    if hour < 0 or hour > 23:
        return False
    if minute < 0 or minute > 59:
        return False
    return True
