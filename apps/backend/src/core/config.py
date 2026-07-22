from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional

from loguru import logger
from pydantic import BaseModel, Field

from src.core.paths import data_dir
from src.core.device import current_device_name

class SyncMode(str, Enum):
    bidirectional = "bidirectional"
    download_only = "download_only"
    upload_only = "upload_only"


class SyncIntervalUnit(str, Enum):
    seconds = "seconds"
    hours = "hours"
    days = "days"


class DeletePolicy(str, Enum):
    off = "off"
    safe = "safe"
    strict = "strict"


class RuntimeProfile(str, Enum):
    production = "production"
    synthetic_test = "synthetic_test"
    snapshot_test = "snapshot_test"
    live_readonly = "live_readonly"
    live_bidirectional = "live_bidirectional"


class CloudWritePolicy(str, Enum):
    deny = "deny"
    allowlisted = "allowlisted"
    normal = "normal"


def _default_config_path() -> Path:
    return data_dir() / "config.json"


def _database_url_from_path(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _default_database_url() -> str:
    return _database_url_from_path(data_dir() / "larksync.db")


REQUIRED_AUTH_SCOPES: tuple[str, ...] = (
    "drive:drive",
    "docx:document",
    "docx:document:readonly",
    "docx:document.block:convert",
    "drive:drive.metadata:readonly",
    "contact:contact.base:readonly",
)

_LEGACY_SCOPE_ALIASES: dict[str, tuple[str, ...]] = {
    "docs:doc": (
        "docx:document",
        "docx:document:readonly",
        "docx:document.block:convert",
    )
}


def _normalize_auth_scopes(scopes: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_scope in scopes or []:
        scope = raw_scope.strip()
        if not scope:
            continue
        mapped_scopes = _LEGACY_SCOPE_ALIASES.get(scope, (scope,))
        for mapped_scope in mapped_scopes:
            if mapped_scope not in seen:
                normalized.append(mapped_scope)
                seen.add(mapped_scope)

    for scope in REQUIRED_AUTH_SCOPES:
        if scope not in seen:
            normalized.append(scope)
            seen.add(scope)

    return normalized


def _default_scopes() -> list[str]:
    return list(REQUIRED_AUTH_SCOPES)


class AppConfig(BaseModel):
    runtime_profile: RuntimeProfile = RuntimeProfile.production
    disable_watcher: bool = False
    disable_scheduler: bool = False
    cloud_write_policy: CloudWritePolicy = CloudWritePolicy.normal
    allowed_cloud_roots: list[str] = Field(default_factory=list)
    feishu_rate_per_second: float = Field(default=8.0, gt=0)
    feishu_rate_burst: int = Field(default=8, ge=1)
    cloud_audit_log: str | None = None
    database_url: str = Field(default_factory=_default_database_url)
    sync_mode: SyncMode = SyncMode.bidirectional
    ignore_hidden_cache_paths: bool = True
    upload_interval_value: float = 60.0
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
    upload_md_to_cloud: bool = False
    device_display_name: str = Field(default_factory=current_device_name)
    delete_policy: DeletePolicy = DeletePolicy.safe
    delete_grace_minutes: int = 30

    auth_authorize_url: str = "https://open.feishu.cn/open-apis/authen/v1/index"
    auth_token_url: str = "https://open.feishu.cn/open-apis/authen/v1/access_token"
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_redirect_uri: str = ""
    auth_scopes: list[str] = Field(default_factory=_default_scopes)
    token_store: str = "keyring"

    @property
    def effective_disable_watcher(self) -> bool:
        return self.disable_watcher or self.runtime_profile in {
            RuntimeProfile.snapshot_test,
            RuntimeProfile.live_readonly,
        }

    @property
    def effective_disable_scheduler(self) -> bool:
        return self.disable_scheduler or self.runtime_profile in {
            RuntimeProfile.snapshot_test,
            RuntimeProfile.live_readonly,
        }

    @property
    def cloud_access_allowed(self) -> bool:
        return self.runtime_profile not in {
            RuntimeProfile.synthetic_test,
            RuntimeProfile.snapshot_test,
        }

    @property
    def effective_cloud_write_policy(self) -> CloudWritePolicy:
        if self.runtime_profile in {
            RuntimeProfile.synthetic_test,
            RuntimeProfile.snapshot_test,
            RuntimeProfile.live_readonly,
        }:
            return CloudWritePolicy.deny
        if self.runtime_profile is RuntimeProfile.live_bidirectional:
            return CloudWritePolicy.allowlisted
        return self.cloud_write_policy


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
        if "auth_scopes" in data:
            data["auth_scopes"] = _normalize_auth_scopes(
                [
                    str(scope)
                    for scope in (data.get("auth_scopes") or [])
                    if isinstance(scope, str)
                ]
            )
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

        env_runtime_profile = os.getenv("LARKSYNC_RUNTIME_PROFILE")
        if env_runtime_profile:
            data["runtime_profile"] = env_runtime_profile.strip()

        for key, env_name in {
            "disable_watcher": "LARKSYNC_DISABLE_WATCHER",
            "disable_scheduler": "LARKSYNC_DISABLE_SCHEDULER",
        }.items():
            env_value = os.getenv(env_name)
            if env_value:
                data[key] = env_value.strip().lower() in {"1", "true", "yes", "on"}

        env_cloud_write_policy = os.getenv("LARKSYNC_CLOUD_WRITE_POLICY")
        if env_cloud_write_policy:
            data["cloud_write_policy"] = env_cloud_write_policy.strip()

        env_allowed_cloud_roots = os.getenv("LARKSYNC_ALLOWED_CLOUD_ROOTS")
        if env_allowed_cloud_roots is not None:
            data["allowed_cloud_roots"] = [
                token.strip()
                for token in env_allowed_cloud_roots.split(",")
                if token.strip()
            ]

        env_feishu_rate = os.getenv("LARKSYNC_FEISHU_RATE_PER_SECOND")
        if env_feishu_rate:
            try:
                data["feishu_rate_per_second"] = float(env_feishu_rate)
            except ValueError:
                pass
        env_feishu_burst = os.getenv("LARKSYNC_FEISHU_RATE_BURST")
        if env_feishu_burst:
            try:
                data["feishu_rate_burst"] = int(env_feishu_burst)
            except ValueError:
                pass
        env_cloud_audit_log = os.getenv("LARKSYNC_CLOUD_AUDIT_LOG")
        if env_cloud_audit_log:
            data["cloud_audit_log"] = env_cloud_audit_log.strip()

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

        env_ignore_hidden_cache = os.getenv("LARKSYNC_IGNORE_HIDDEN_CACHE_PATHS")
        if env_ignore_hidden_cache:
            data["ignore_hidden_cache_paths"] = (
                env_ignore_hidden_cache.strip().lower() in {"1", "true", "yes", "on"}
            )

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
        data["auth_scopes"] = _normalize_auth_scopes(
            [
                str(scope)
                for scope in (data.get("auth_scopes") or [])
                if isinstance(scope, str)
            ]
        )

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

        env_delete_policy = os.getenv("LARKSYNC_DELETE_POLICY")
        if env_delete_policy:
            data["delete_policy"] = env_delete_policy

        env_delete_grace = os.getenv("LARKSYNC_DELETE_GRACE_MINUTES")
        if env_delete_grace:
            try:
                data["delete_grace_minutes"] = int(env_delete_grace)
            except ValueError:
                pass

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
        # 仅修正已知错误的端点，正确的 v1 端点保持不变。
        _CORRECT_AUTHORIZE = AppConfig.model_fields["auth_authorize_url"].default
        _CORRECT_TOKEN = AppConfig.model_fields["auth_token_url"].default
        _WRONG_AUTHORIZE_URLS = {
            "https://open.feishu.cn/open-apis/authen/v1/authorize",
            "https://accounts.feishu.cn/open-apis/authen/v1/authorize",
        }
        _WRONG_TOKEN_URLS = {
            "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
            "https://open.feishu.cn/open-apis/authen/v2/oauth/token",
        }
        saved_authorize = (data.get("auth_authorize_url") or "").strip()
        saved_token_url = (data.get("auth_token_url") or "").strip()
        if saved_authorize in _WRONG_AUTHORIZE_URLS:
            logger.info(
                "迁移 auth_authorize_url: {} → {}", saved_authorize, _CORRECT_AUTHORIZE
            )
            data["auth_authorize_url"] = _CORRECT_AUTHORIZE
        if saved_token_url in _WRONG_TOKEN_URLS:
            logger.info(
                "迁移 auth_token_url: {} → {}", saved_token_url, _CORRECT_TOKEN
            )
            data["auth_token_url"] = _CORRECT_TOKEN

        # v0.8.2 将正式版默认端口从 8000 迁移到 18765。仅迁移精确匹配的
        # 本地旧回调，用户自定义域名、路径或显式环境变量保持不变。
        saved_redirect = str(data.get("auth_redirect_uri") or "").strip()
        legacy_redirects = {
            "http://localhost:8000/auth/callback": "http://localhost:18765/auth/callback",
            "http://127.0.0.1:8000/auth/callback": "http://127.0.0.1:18765/auth/callback",
        }
        if saved_redirect in legacy_redirects and not os.getenv("LARKSYNC_AUTH_REDIRECT_URI"):
            data["auth_redirect_uri"] = legacy_redirects[saved_redirect]

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
