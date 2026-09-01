from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional

import keyring
from loguru import logger

from .config import ConfigManager
from .paths import data_dir


@dataclass(frozen=True)
class TokenData:
    access_token: str
    refresh_token: str
    expires_at: Optional[float]
    open_id: Optional[str] = None
    account_name: Optional[str] = None
    scope: Optional[str] = None
    refresh_expires_at: Optional[float] = None
    auth_protocol: str = "device_v2"

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - leeway_seconds)


class TokenStore:
    def get(self) -> Optional[TokenData]:
        raise NotImplementedError

    def reload(self) -> Optional[TokenData]:
        """绕过进程内缓存，重新读取持久化凭据。"""
        return self.get()

    def set(self, token: TokenData) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class CredentialStorageError(RuntimeError):
    """系统安全凭据读写失败；异常消息不得包含凭据内容。"""


class SecretStore:
    def get(self, namespace: str) -> Optional[str]:
        raise NotImplementedError

    def set(self, namespace: str, value: str) -> None:
        raise NotImplementedError

    def clear(self, namespace: str) -> None:
        raise NotImplementedError


class KeyringSecretStore(SecretStore):
    _service = "larksync.app-profile"

    def get(self, namespace: str) -> Optional[str]:
        return keyring.get_password(self._service, namespace)

    def set(self, namespace: str, value: str) -> None:
        keyring.set_password(self._service, namespace, value)

    def clear(self, namespace: str) -> None:
        try:
            keyring.delete_password(self._service, namespace)
        except keyring.errors.PasswordDeleteError:
            pass


class MemorySecretStore(SecretStore):
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, namespace: str) -> Optional[str]:
        return self._values.get(namespace)

    def set(self, namespace: str, value: str) -> None:
        self._values[namespace] = value

    def clear(self, namespace: str) -> None:
        self._values.pop(namespace, None)


class KeyringTokenStore(TokenStore):
    """使用分片 Token 包和活动清单规避 Windows CredWrite 长度限制。"""

    _service = "larksync"
    _BUNDLE_FORMAT = "chunked_bundle_v1"
    _KEY_ACTIVE_BUNDLE = "token_bundle.active"
    _KEY_STAGING_BUNDLE = "token_bundle.staging"
    _BUNDLE_KEY_PREFIX = "token_bundle"
    _CHUNK_SIZE = 900
    _MAX_CHUNKS = 128
    # 拆分存储的 key
    _KEY_ACCESS = "access_token"
    _KEY_REFRESH = "refresh_token"
    _KEY_EXPIRES = "expires_at"
    _KEY_OPEN_ID = "open_id"
    _KEY_ACCOUNT_NAME = "account_name"
    # 旧版合并存储 key（兼容迁移）
    _KEY_LEGACY = "oauth_tokens"

    def __init__(self, account_id: str | None = None) -> None:
        self._service = (
            f"larksync.account.{account_id.strip()}"
            if account_id and account_id.strip()
            else self._service
        )
        self._cache_lock = RLock()
        self._cache_loaded = False
        self._cached_token: Optional[TokenData] = None

    def get(self) -> Optional[TokenData]:
        with self._cache_lock:
            if self._cache_loaded:
                return self._cached_token
            self._cached_token = self._read_from_keyring()
            self._cache_loaded = True
            return self._cached_token

    def _read_from_keyring(self) -> Optional[TokenData]:
        # Windows 凭据管理器属于同步系统调用，只允许首次加载或显式 reload。
        try:
            active_manifest = keyring.get_password(
                self._service, self._KEY_ACTIVE_BUNDLE
            )
            if active_manifest:
                token = self._read_bundle(active_manifest)
                self._recover_interrupted_staging(active_manifest)
                return token
            token = self._read_legacy_formats()
            self._recover_interrupted_staging(None)
            return token
        except CredentialStorageError:
            raise
        except Exception as exc:
            raise CredentialStorageError("系统安全凭据读取失败") from exc

    def _read_legacy_formats(self) -> Optional[TokenData]:
        access_token = keyring.get_password(self._service, self._KEY_ACCESS)
        if access_token:
            refresh_raw = keyring.get_password(self._service, self._KEY_REFRESH) or ""
            refresh_token = "" if refresh_raw == "_empty_" else refresh_raw
            expires_raw = keyring.get_password(self._service, self._KEY_EXPIRES)
            expires_at = float(expires_raw) if expires_raw else None
            open_id_raw = keyring.get_password(self._service, self._KEY_OPEN_ID)
            account_name_raw = keyring.get_password(self._service, self._KEY_ACCOUNT_NAME)
            scope_raw = keyring.get_password(self._service, "scope")
            refresh_expires_raw = keyring.get_password(
                self._service, "refresh_expires_at"
            )
            auth_protocol_raw = keyring.get_password(self._service, "auth_protocol")
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                open_id=open_id_raw.strip() if open_id_raw else None,
                account_name=account_name_raw.strip() if account_name_raw else None,
                scope=scope_raw.strip() if scope_raw else None,
                refresh_expires_at=(
                    float(refresh_expires_raw) if refresh_expires_raw else None
                ),
                auth_protocol=(auth_protocol_raw or "device_v2").strip() or "device_v2",
            )
        raw = keyring.get_password(self._service, self._KEY_LEGACY)
        if not raw:
            return None
        data = json.loads(raw)
        return self._token_from_payload(data, default_protocol="legacy_v1")

    def _read_bundle(self, manifest_raw: str) -> TokenData:
        try:
            manifest = json.loads(manifest_raw)
            if not isinstance(manifest, dict):
                raise ValueError("活动清单不是对象")
            if manifest.get("format") != self._BUNDLE_FORMAT:
                raise ValueError("活动清单格式不支持")
            generation = str(manifest.get("generation") or "")
            if len(generation) != 32 or any(
                char not in "0123456789abcdef" for char in generation
            ):
                raise ValueError("活动清单 generation 无效")
            chunk_count = int(manifest.get("chunks") or 0)
            if chunk_count < 1 or chunk_count > self._MAX_CHUNKS:
                raise ValueError("活动清单分片数量无效")
            encoded_length = int(manifest.get("encoded_length") or 0)
            expected_sha256 = str(manifest.get("sha256") or "")
            if encoded_length < 1 or len(expected_sha256) != 64:
                raise ValueError("活动清单校验字段无效")

            chunks: list[str] = []
            for index in range(chunk_count):
                key = self._chunk_key(generation, index)
                value = keyring.get_password(self._service, key)
                if value is None:
                    raise ValueError(f"活动凭据缺少分片 {index}")
                chunks.append(value)
            encoded = "".join(chunks)
            digest = hashlib.sha256(encoded.encode("ascii")).hexdigest()
            if len(encoded) != encoded_length or digest != expected_sha256:
                raise ValueError("活动凭据长度或摘要不一致")
            payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))
            return self._token_from_payload(payload, default_protocol="device_v2")
        except CredentialStorageError:
            raise
        except Exception as exc:
            raise CredentialStorageError("系统安全凭据校验失败") from exc

    @staticmethod
    def _token_from_payload(
        payload: object, *, default_protocol: str
    ) -> TokenData:
        if not isinstance(payload, dict):
            raise ValueError("Token 包不是对象")
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token", "")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Token 包缺少 access_token")
        if not isinstance(refresh_token, str):
            raise ValueError("Token 包 refresh_token 无效")
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=KeyringTokenStore._optional_float(payload.get("expires_at")),
            open_id=KeyringTokenStore._optional_text(payload.get("open_id")),
            account_name=KeyringTokenStore._optional_text(
                payload.get("account_name")
            ),
            scope=KeyringTokenStore._optional_text(payload.get("scope")),
            refresh_expires_at=KeyringTokenStore._optional_float(
                payload.get("refresh_expires_at")
            ),
            auth_protocol=(
                KeyringTokenStore._optional_text(payload.get("auth_protocol"))
                or default_protocol
            ),
        )

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float, str)):
            return float(value)
        raise ValueError("时间字段无效")

    def reload(self) -> Optional[TokenData]:
        with self._cache_lock:
            self._cached_token = self._read_from_keyring()
            self._cache_loaded = True
            return self._cached_token

    def set(self, token: TokenData) -> None:
        with self._cache_lock:
            try:
                previous_manifest = keyring.get_password(
                    self._service, self._KEY_ACTIVE_BUNDLE
                )
            except Exception as exc:
                raise CredentialStorageError("系统安全凭据读取失败") from exc
            self._recover_interrupted_staging(previous_manifest)
            generation = uuid.uuid4().hex
            encoded = self._encode_token(token)
            chunks = [
                encoded[index : index + self._CHUNK_SIZE]
                for index in range(0, len(encoded), self._CHUNK_SIZE)
            ]
            if not chunks or len(chunks) > self._MAX_CHUNKS:
                raise CredentialStorageError("系统安全凭据长度超过支持范围")
            manifest = self._build_manifest(generation, chunks)
            manifest_raw = json.dumps(
                manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True
            )
            written_keys: list[str] = []
            switched = False
            try:
                keyring.set_password(
                    self._service, self._KEY_STAGING_BUNDLE, manifest_raw
                )
                for index, chunk in enumerate(chunks):
                    key = self._chunk_key(generation, index)
                    keyring.set_password(self._service, key, chunk)
                    written_keys.append(key)
                if self._read_bundle(manifest_raw) != token:
                    raise CredentialStorageError("系统安全凭据回读不一致")
                keyring.set_password(
                    self._service, self._KEY_ACTIVE_BUNDLE, manifest_raw
                )
                switched = True
                if self._read_from_keyring() != token:
                    raise CredentialStorageError("系统安全凭据切换校验失败")
            except Exception as exc:
                if switched:
                    self._restore_active_manifest(previous_manifest)
                for key in written_keys:
                    self._delete_key_quietly(key)
                self._delete_key_quietly(self._KEY_STAGING_BUNDLE)
                if isinstance(exc, CredentialStorageError):
                    raise
                raise CredentialStorageError("系统安全凭据写入失败") from exc

            self._cached_token = token
            self._cache_loaded = True

            self._delete_key_quietly(self._KEY_STAGING_BUNDLE)
            self._cleanup_previous_generation(previous_manifest, generation)
            for key in self._legacy_keys():
                self._delete_key_quietly(key)

    @staticmethod
    def _encode_token(token: TokenData) -> str:
        payload = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "open_id": token.open_id,
            "account_name": token.account_name,
            "scope": token.scope,
            "refresh_expires_at": token.refresh_expires_at,
            "auth_protocol": token.auth_protocol,
        }
        raw = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _build_manifest(
        self, generation: str, chunks: list[str]
    ) -> dict[str, object]:
        encoded = "".join(chunks)
        return {
            "format": self._BUNDLE_FORMAT,
            "generation": generation,
            "chunks": len(chunks),
            "encoded_length": len(encoded),
            "sha256": hashlib.sha256(encoded.encode("ascii")).hexdigest(),
        }

    def _restore_active_manifest(self, previous_manifest: str | None) -> None:
        try:
            if previous_manifest:
                keyring.set_password(
                    self._service, self._KEY_ACTIVE_BUNDLE, previous_manifest
                )
            else:
                self._delete_key(self._KEY_ACTIVE_BUNDLE)
        except Exception as exc:
            logger.error(
                "系统安全凭据活动清单恢复失败: service={} error_type={}",
                self._service,
                type(exc).__name__,
            )

    def _cleanup_previous_generation(
        self, manifest_raw: str | None, active_generation: str
    ) -> None:
        if not manifest_raw:
            return
        try:
            manifest = json.loads(manifest_raw)
            generation = str(manifest.get("generation") or "")
            chunk_count = int(manifest.get("chunks") or 0)
            generation_valid = len(generation) == 32 and all(
                char in "0123456789abcdef" for char in generation
            )
            if (
                not generation_valid
                or generation == active_generation
                or not (1 <= chunk_count <= self._MAX_CHUNKS)
            ):
                return
            for index in range(chunk_count):
                self._delete_key_quietly(self._chunk_key(generation, index))
        except Exception as exc:
            logger.warning(
                "旧版系统安全凭据清理跳过: service={} error_type={}",
                self._service,
                type(exc).__name__,
            )

    def _recover_interrupted_staging(
        self, active_manifest_raw: str | None
    ) -> None:
        try:
            staging_raw = keyring.get_password(
                self._service, self._KEY_STAGING_BUNDLE
            )
            if not staging_raw:
                return
            staging = json.loads(staging_raw)
            generation = str(staging.get("generation") or "")
            active_generation = ""
            if active_manifest_raw:
                active_manifest = json.loads(active_manifest_raw)
                active_generation = str(active_manifest.get("generation") or "")
            if generation and generation != active_generation:
                self._cleanup_previous_generation(staging_raw, active_generation)
            self._delete_key_quietly(self._KEY_STAGING_BUNDLE)
        except Exception as exc:
            logger.warning(
                "未完成系统安全凭据清理跳过: service={} error_type={}",
                self._service,
                type(exc).__name__,
            )

    @classmethod
    def _chunk_key(cls, generation: str, index: int) -> str:
        return f"{cls._BUNDLE_KEY_PREFIX}.{generation}.{index:04d}"

    def _legacy_keys(self) -> tuple[str, ...]:
        return (
            self._KEY_ACCESS,
            self._KEY_REFRESH,
            self._KEY_EXPIRES,
            self._KEY_OPEN_ID,
            self._KEY_ACCOUNT_NAME,
            self._KEY_LEGACY,
            "scope",
            "refresh_expires_at",
            "auth_protocol",
        )

    def _delete_key(self, key: str) -> None:
        try:
            keyring.delete_password(self._service, key)
        except keyring.errors.PasswordDeleteError:
            pass

    def _delete_key_quietly(self, key: str) -> None:
        try:
            self._delete_key(key)
        except Exception as exc:
            logger.warning(
                "系统安全凭据清理失败: service={} key={} error_type={}",
                self._service,
                key,
                type(exc).__name__,
            )

    def clear(self) -> None:
        with self._cache_lock:
            active_manifest = keyring.get_password(
                self._service, self._KEY_ACTIVE_BUNDLE
            )
            staging_manifest = keyring.get_password(
                self._service, self._KEY_STAGING_BUNDLE
            )
            if active_manifest:
                self._cleanup_previous_generation(active_manifest, "")
            if staging_manifest:
                self._cleanup_previous_generation(staging_manifest, "")
            self._delete_key(self._KEY_ACTIVE_BUNDLE)
            self._delete_key(self._KEY_STAGING_BUNDLE)
            for key in self._legacy_keys():
                self._delete_key(key)
            self._cached_token = None
            self._cache_loaded = True


class MemoryTokenStore(TokenStore):
    def __init__(self) -> None:
        self._token: Optional[TokenData] = None

    def get(self) -> Optional[TokenData]:
        return self._token

    def reload(self) -> Optional[TokenData]:
        return self._token

    def set(self, token: TokenData) -> None:
        self._token = token

    def clear(self) -> None:
        self._token = None


class FileTokenStore(TokenStore):
    """用于无桌面 keyring 环境（如 WSL/CI）的文件凭证存储。"""

    def __init__(self, path: Path | None = None, account_id: str | None = None) -> None:
        env_path = os.getenv("LARKSYNC_TOKEN_FILE")
        target = path
        if target is None and env_path:
            target = Path(env_path).expanduser()
        if target is None:
            target = data_dir() / "token_store.json"
        if account_id and account_id.strip():
            safe_id = "".join(
                char if char.isalnum() or char in {"-", "_"} else "_"
                for char in account_id.strip()
            )
            target = target.with_name(f"{target.stem}.{safe_id}{target.suffix}")
        self._path = target.resolve()

    def get(self) -> Optional[TokenData]:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return None
        refresh_token = payload.get("refresh_token", "")
        if not isinstance(refresh_token, str):
            refresh_token = ""
        expires_raw = payload.get("expires_at")
        expires_at: Optional[float] = None
        if isinstance(expires_raw, (int, float)):
            expires_at = float(expires_raw)
        elif isinstance(expires_raw, str) and expires_raw.strip():
            try:
                expires_at = float(expires_raw)
            except ValueError:
                expires_at = None
        open_id = payload.get("open_id")
        if not isinstance(open_id, str) or not open_id.strip():
            open_id = None
        account_name = payload.get("account_name")
        if not isinstance(account_name, str) or not account_name.strip():
            account_name = None
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            open_id=open_id.strip() if open_id else None,
            account_name=account_name.strip() if account_name else None,
            scope=(
                payload.get("scope").strip()
                if isinstance(payload.get("scope"), str)
                and payload.get("scope").strip()
                else None
            ),
            refresh_expires_at=(
                float(payload["refresh_expires_at"])
                if isinstance(payload.get("refresh_expires_at"), (int, float))
                else None
            ),
            auth_protocol=(
                payload.get("auth_protocol").strip()
                if isinstance(payload.get("auth_protocol"), str)
                and payload.get("auth_protocol").strip()
                else "device_v2"
            ),
        )

    def reload(self) -> Optional[TokenData]:
        return self.get()

    def set(self, token: TokenData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "open_id": token.open_id,
            "account_name": token.account_name,
            "scope": token.scope,
            "refresh_expires_at": token.refresh_expires_at,
            "auth_protocol": token.auth_protocol,
        }
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_path, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    def clear(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


_shared_token_stores: dict[tuple[str, str], TokenStore] = {}
_shared_secret_store: SecretStore | None = None


def get_token_store(account_id: str | None = None) -> TokenStore:
    from .account_context import current_account_id

    config = ConfigManager.get().config
    store = os.getenv("LARKSYNC_TOKEN_STORE", config.token_store).lower()
    resolved_account_id = (account_id or current_account_id() or "").strip()
    cache_key = (store, resolved_account_id)
    cached = _shared_token_stores.get(cache_key)
    if cached is not None:
        return cached
    if store == "memory":
        cached = MemoryTokenStore()
    elif store == "file":
        cached = FileTokenStore(account_id=resolved_account_id or None)
    else:
        cached = KeyringTokenStore(account_id=resolved_account_id or None)
    _shared_token_stores[cache_key] = cached
    return cached


def get_secret_store() -> SecretStore:
    global _shared_secret_store
    if _shared_secret_store is None:
        _shared_secret_store = KeyringSecretStore()
    return _shared_secret_store
