from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from src.core.paths import data_dir

class SyncMode(str, Enum):
    bidirectional = "bidirectional"
    download_only = "download_only"
    upload_only = "upload_only"


class SyncIntervalUnit(str, Enum):
    seconds = "seconds"
    hours = "hours"
    days = "days"


def _default_config_path() -> Path:
    return data_dir() / "config.json"


def _database_url_from_path(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _default_database_url() -> str:
    return _database_url_from_path(data_dir() / "larksync.db")


def _default_scopes() -> list[str]:
    return [
        "drive:drive",
        "docs:doc",
        "drive:drive.metadata:readonly",
        "contact:contact.base:readonly",
    ]


class AppConfig(BaseModel):
    database_url: str = Field(default_factory=_default_database_url)
    sync_mode: SyncMode = SyncMode.bidirectional
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

    auth_authorize_url: str = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
    auth_token_url: str = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_redirect_uri: str = ""
    auth_scopes: list[str] = Field(default_factory=_default_scopes)
    token_store: str = "keyring"


class ConfigManager:
    _instance: ClassVar[Optional["ConfigManager"]] = None

    def __init__(self, config_path: Optional[Path] = None) -> None:
        env_path = os.getenv("LARKSYNC_CONFIG")
        if config_path is None and env_path:
            config_path = Path(env_path)
        self._config_path = (config_path or _default_config_path()).expanduser()
        self._config = self._load_config()

    @property
    def config(self) -> AppConfig:
        return self._config

    def reload(self) -> AppConfig:
        self._config = self._load_config()
        return self._config

    @property
    def config_path(self) -> Path:
        return self._config_path

    def save_config(self, data: dict[str, object]) -> AppConfig:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._config = self._load_config()
        return self._config

    def _load_config(self) -> AppConfig:
        data: dict[str, object] = {}
        if self._config_path.exists():
            data = json.loads(self._config_path.read_text(encoding="utf-8"))

        env_db_url = os.getenv("LARKSYNC_DATABASE_URL")
        env_db_path = os.getenv("LARKSYNC_DB_PATH")
        if env_db_url:
            data["database_url"] = env_db_url
        elif env_db_path:
            data["database_url"] = _database_url_from_path(
                Path(env_db_path).expanduser().resolve()
            )

        env_sync_mode = os.getenv("LARKSYNC_SYNC_MODE")
        if env_sync_mode:
            data["sync_mode"] = env_sync_mode

        env_upload_interval = os.getenv("LARKSYNC_UPLOAD_INTERVAL_SECONDS")
        if env_upload_interval:
            try:
                data["upload_interval_value"] = float(env_upload_interval)
                data.setdefault("upload_interval_unit", SyncIntervalUnit.seconds.value)
            except ValueError:
                pass

        env_upload_value = os.getenv("LARKSYNC_UPLOAD_INTERVAL_VALUE")
        if env_upload_value:
            try:
                data["upload_interval_value"] = float(env_upload_value)
            except ValueError:
                pass

        env_upload_unit = os.getenv("LARKSYNC_UPLOAD_INTERVAL_UNIT")
        if env_upload_unit:
            data["upload_interval_unit"] = env_upload_unit

        env_upload_time = os.getenv("LARKSYNC_UPLOAD_DAILY_TIME")
        if env_upload_time:
            data["upload_daily_time"] = env_upload_time

        env_download_value = os.getenv("LARKSYNC_DOWNLOAD_INTERVAL_VALUE")
        if env_download_value:
            try:
                data["download_interval_value"] = float(env_download_value)
            except ValueError:
                pass

        env_download_unit = os.getenv("LARKSYNC_DOWNLOAD_INTERVAL_UNIT")
        if env_download_unit:
            data["download_interval_unit"] = env_download_unit

        env_download_time = os.getenv("LARKSYNC_DOWNLOAD_DAILY_TIME")
        if env_download_time:
            data["download_daily_time"] = env_download_time

        env_scopes = os.getenv("LARKSYNC_AUTH_SCOPES")
        if env_scopes:
            data["auth_scopes"] = [
                scope.strip() for scope in env_scopes.split(",") if scope.strip()
            ]

        env_sync_log_retention = os.getenv("LARKSYNC_SYNC_LOG_RETENTION_DAYS")
        if env_sync_log_retention:
            try:
                data["sync_log_retention_days"] = int(env_sync_log_retention)
            except ValueError:
                pass

        env_sync_log_warn = os.getenv("LARKSYNC_SYNC_LOG_WARN_SIZE_MB")
        if env_sync_log_warn:
            try:
                data["sync_log_warn_size_mb"] = int(env_sync_log_warn)
            except ValueError:
                pass

        env_system_log_retention = os.getenv("LARKSYNC_SYSTEM_LOG_RETENTION_DAYS")
        if env_system_log_retention:
            try:
                data["system_log_retention_days"] = int(env_system_log_retention)
            except ValueError:
                pass

        env_auto_update = os.getenv("LARKSYNC_AUTO_UPDATE_ENABLED")
        if env_auto_update:
            data["auto_update_enabled"] = env_auto_update.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        env_update_interval = os.getenv("LARKSYNC_UPDATE_CHECK_INTERVAL_HOURS")
        if env_update_interval:
            try:
                data["update_check_interval_hours"] = int(env_update_interval)
            except ValueError:
                pass

        env_allow_dev = os.getenv("LARKSYNC_ALLOW_DEV_TO_STABLE")
        if env_allow_dev:
            data["allow_dev_to_stable"] = env_allow_dev.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        for key, env_name in {
            "auth_authorize_url": "LARKSYNC_AUTH_AUTHORIZE_URL",
            "auth_token_url": "LARKSYNC_AUTH_TOKEN_URL",
            "auth_client_id": "LARKSYNC_AUTH_CLIENT_ID",
            "auth_client_secret": "LARKSYNC_AUTH_CLIENT_SECRET",
            "auth_redirect_uri": "LARKSYNC_AUTH_REDIRECT_URI",
            "token_store": "LARKSYNC_TOKEN_STORE",
        }.items():
            env_value = os.getenv(env_name)
            if env_value:
                data[key] = env_value

        # ---- 旧 OAuth 端点迁移 ----
        _OLD_AUTHORIZE_URLS = {
            "https://open.feishu.cn/open-apis/authen/v1/authorize",
        }
        _OLD_TOKEN_URLS = {
            "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
        }
        if data.get("auth_authorize_url") in _OLD_AUTHORIZE_URLS:
            data["auth_authorize_url"] = AppConfig.model_fields[
                "auth_authorize_url"
            ].default
        if data.get("auth_token_url") in _OLD_TOKEN_URLS:
            data["auth_token_url"] = AppConfig.model_fields[
                "auth_token_url"
            ].default

        if "upload_interval_value" not in data and "upload_interval_seconds" in data:
            try:
                data["upload_interval_value"] = float(data["upload_interval_seconds"])
                data.setdefault("upload_interval_unit", SyncIntervalUnit.seconds.value)
            except (TypeError, ValueError):
                pass

        return AppConfig.model_validate(data)

    @classmethod
    def get(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
