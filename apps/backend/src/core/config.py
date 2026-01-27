from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel, Field


class SyncMode(str, Enum):
    bidirectional = "bidirectional"
    download_only = "download_only"
    upload_only = "upload_only"


def _repo_root() -> Path:
    env_root = os.getenv("LARKSYNC_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[4]


def _default_config_path() -> Path:
    return _repo_root() / "data" / "config.json"


def _database_url_from_path(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _default_database_url() -> str:
    return _database_url_from_path(_repo_root() / "data" / "larksync.db")


def _default_scopes() -> list[str]:
    return [
        "drive:drive",
        "docs:doc",
        "drive:meta",
        "contact:contact.base:readonly",
    ]


class AppConfig(BaseModel):
    database_url: str = Field(default_factory=_default_database_url)
    sync_mode: SyncMode = SyncMode.bidirectional

    auth_authorize_url: str = ""
    auth_token_url: str = ""
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

        env_scopes = os.getenv("LARKSYNC_AUTH_SCOPES")
        if env_scopes:
            data["auth_scopes"] = [
                scope.strip() for scope in env_scopes.split(",") if scope.strip()
            ]

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

        return AppConfig.model_validate(data)

    @classmethod
    def get(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
