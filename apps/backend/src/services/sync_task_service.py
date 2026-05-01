from __future__ import annotations

import time
import uuid
import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import ConfigManager, DeletePolicy
from src.core.device import current_device_id
from src.core.security import get_token_store
from src.db.models import SyncTask
from src.db.session import get_session_maker

_OWNER_OPEN_ID_UNSET = object()
_MD_SYNC_MODE_ENHANCED = "enhanced"
_MD_SYNC_MODE_DOWNLOAD_ONLY = "download_only"
_MD_SYNC_MODE_DOC_ONLY = "doc_only"
_MD_SYNC_MODE_VALUES = {
    _MD_SYNC_MODE_ENHANCED,
    _MD_SYNC_MODE_DOWNLOAD_ONLY,
    _MD_SYNC_MODE_DOC_ONLY,
}


@dataclass
class SyncTaskItem:
    id: str
    name: str | None
    local_path: str
    cloud_folder_token: str
    cloud_folder_name: str | None
    base_path: str | None
    sync_mode: str
    update_mode: str
    enabled: bool
    created_at: float
    updated_at: float
    last_run_at: float | None = None
    md_sync_mode: str = _MD_SYNC_MODE_ENHANCED
    ignored_subpaths: list[str] = field(default_factory=list)
    delete_policy: str | None = None
    delete_grace_minutes: int | None = None
    owner_device_id: str | None = None
    owner_open_id: str | None = None
    is_test: bool = False


class SyncTaskValidationError(ValueError):
    pass


class SyncTaskService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        owner_device_id: str | None = None,
        owner_open_id: str | None | object = _OWNER_OPEN_ID_UNSET,
    ) -> None:
        self._session_maker = session_maker or get_session_maker()
        self._owner_device_id = owner_device_id or current_device_id()
        self._owner_open_id = owner_open_id

    async def create_task(
        self,
        *,
        name: str | None,
        local_path: str,
        cloud_folder_token: str,
        cloud_folder_name: str | None = None,
        base_path: str | None,
        sync_mode: str,
        update_mode: str = "auto",
        md_sync_mode: str = _MD_SYNC_MODE_ENHANCED,
        ignored_subpaths: list[str] | None = None,
        delete_policy: str | None = None,
        delete_grace_minutes: int | None = None,
        is_test: bool = False,
        enabled: bool = True,
        owner_open_id: str | None = None,
    ) -> SyncTaskItem:
        now = time.time()
        clean_name = self._clean_optional_text(name)
        clean_local_path = self._clean_required_text(
            local_path, field_name="本地目录", normalize=False
        )
        clean_cloud_folder_token = self._clean_required_text(
            cloud_folder_token, field_name="云端目录 Token", normalize=False
        )
        clean_cloud_folder_name = self._clean_optional_text(cloud_folder_name)
        clean_base_path = self._clean_optional_text(base_path)
        resolved_ignored_subpaths = self._normalize_ignored_subpaths(
            clean_local_path,
            ignored_subpaths,
        )
        resolved_open_id = owner_open_id or self._effective_owner_open_id()
        resolved_delete_policy, resolved_delete_grace = self._resolve_task_delete_settings(
            delete_policy=delete_policy,
            delete_grace_minutes=delete_grace_minutes,
        )
        record = SyncTask(
            id=str(uuid.uuid4()),
            name=clean_name,
            local_path=clean_local_path,
            cloud_folder_token=clean_cloud_folder_token,
            cloud_folder_name=clean_cloud_folder_name,
            base_path=clean_base_path,
            sync_mode=sync_mode,
            update_mode=update_mode,
            md_sync_mode=self._normalize_md_sync_mode(md_sync_mode),
            ignored_subpaths=self._serialize_ignored_subpaths(resolved_ignored_subpaths),
            delete_policy=resolved_delete_policy,
            delete_grace_minutes=resolved_delete_grace,
            is_test=bool(is_test),
            owner_device_id=self._owner_device_id,
            owner_open_id=resolved_open_id,
            enabled=enabled,
            created_at=now,
            updated_at=now,
            last_run_at=None,
        )
        async with self._session_maker() as session:
            await self._validate_task_mapping(
                session=session,
                local_path=clean_local_path,
                cloud_folder_token=clean_cloud_folder_token,
                cloud_folder_name=clean_cloud_folder_name,
                exclude_task_id=None,
            )
            session.add(record)
            await session.commit()
        return self._to_item(record)

    async def list_tasks(self) -> list[SyncTaskItem]:
        stmt = (
            select(SyncTask)
            .where(SyncTask.owner_device_id == self._owner_device_id)
            .order_by(SyncTask.created_at.desc())
        )
        open_id = self._effective_owner_open_id()
        if open_id:
            stmt = stmt.where(
                or_(
                    SyncTask.owner_open_id == open_id,
                    SyncTask.owner_open_id.is_(None),
                    SyncTask.owner_open_id == "",
                )
            )
        async with self._session_maker() as session:
            result = await session.execute(stmt)
            records = result.scalars().all()
            changed = False
            visible: list[SyncTask] = []
            for record in records:
                changed = self._migrate_owner_open_id_if_local(record) or changed
                if self._owner_matches(record):
                    visible.append(record)
            if changed:
                await session.commit()
        return [self._to_item(record) for record in visible]

    async def get_task(self, task_id: str) -> SyncTaskItem | None:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return None
            migrated = self._migrate_owner_open_id_if_local(record)
            if not self._owner_matches(record):
                return None
            if migrated:
                await session.commit()
            return self._to_item(record)

    async def update_task(
        self,
        task_id: str,
        *,
        name: str | None = None,
        local_path: str | None = None,
        cloud_folder_token: str | None = None,
        cloud_folder_name: str | None = None,
        base_path: str | None = None,
        sync_mode: str | None = None,
        update_mode: str | None = None,
        md_sync_mode: str | None = None,
        ignored_subpaths: list[str] | None = None,
        delete_policy: str | None = None,
        delete_grace_minutes: int | None = None,
        is_test: bool | None = None,
        enabled: bool | None = None,
    ) -> SyncTaskItem | None:
        open_id = self._effective_owner_open_id()
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return None
            self._migrate_owner_open_id_if_local(record)
            if not self._owner_matches(record):
                return None
            target_local_path = (
                self._clean_required_text(
                    local_path, field_name="本地目录", normalize=False
                )
                if local_path is not None
                else record.local_path
            )
            target_cloud_folder_token = (
                self._clean_required_text(
                    cloud_folder_token, field_name="云端目录 Token", normalize=False
                )
                if cloud_folder_token is not None
                else record.cloud_folder_token
            )
            target_cloud_folder_name = (
                self._clean_optional_text(cloud_folder_name)
                if cloud_folder_name is not None
                else record.cloud_folder_name
            )
            target_ignored_subpaths = (
                self._normalize_ignored_subpaths(target_local_path, ignored_subpaths)
                if ignored_subpaths is not None
                else self._parse_ignored_subpaths(record.ignored_subpaths)
            )
            await self._validate_task_mapping(
                session=session,
                local_path=target_local_path,
                cloud_folder_token=target_cloud_folder_token,
                cloud_folder_name=target_cloud_folder_name,
                exclude_task_id=record.id,
            )
            if name is not None:
                record.name = self._clean_optional_text(name)
            if local_path is not None:
                record.local_path = target_local_path
            if cloud_folder_token is not None:
                record.cloud_folder_token = target_cloud_folder_token
            if cloud_folder_name is not None:
                record.cloud_folder_name = target_cloud_folder_name
            if base_path is not None:
                record.base_path = self._clean_optional_text(base_path)
            if sync_mode is not None:
                record.sync_mode = sync_mode
            if update_mode is not None:
                record.update_mode = update_mode
            if md_sync_mode is not None:
                record.md_sync_mode = self._normalize_md_sync_mode(md_sync_mode)
            if ignored_subpaths is not None:
                record.ignored_subpaths = self._serialize_ignored_subpaths(
                    target_ignored_subpaths
                )
            if delete_policy is not None:
                record.delete_policy = self._normalize_delete_policy(delete_policy)
            if delete_grace_minutes is not None and delete_grace_minutes >= 0:
                record.delete_grace_minutes = int(delete_grace_minutes)
            if (
                record.delete_policy == DeletePolicy.strict.value
                and (record.delete_grace_minutes or 0) != 0
            ):
                record.delete_grace_minutes = 0
            if is_test is not None:
                record.is_test = bool(is_test)
            if enabled is not None:
                record.enabled = enabled
            if open_id and not record.owner_open_id:
                record.owner_open_id = open_id
            record.updated_at = time.time()
            await session.commit()
            return self._to_item(record)

    async def delete_task(self, task_id: str) -> bool:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return False
            self._migrate_owner_open_id_if_local(record)
            if not self._owner_matches(record):
                return False
            await session.delete(record)
            await session.commit()
            return True

    async def mark_task_run(
        self, task_id: str, run_at: float | None = None
    ) -> bool:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return False
            self._migrate_owner_open_id_if_local(record)
            if not self._owner_matches(record):
                return False
            now = time.time() if run_at is None else float(run_at)
            record.last_run_at = now
            record.updated_at = now
            await session.commit()
            return True

    def _effective_owner_open_id(self) -> str | None:
        if self._owner_open_id is not _OWNER_OPEN_ID_UNSET:
            if isinstance(self._owner_open_id, str):
                value = self._owner_open_id.strip()
                return value or None
            return None
        try:
            token = get_token_store().get()
        except Exception:
            return None
        if token and token.open_id:
            return token.open_id
        return None

    def _owner_matches(self, record: SyncTask) -> bool:
        if record.owner_device_id != self._owner_device_id:
            return False
        open_id = self._effective_owner_open_id()
        if not open_id:
            return True
        return record.owner_open_id == open_id

    def _migrate_owner_open_id_if_local(self, record: SyncTask) -> bool:
        """
        仅对“本机可确认属于当前设备”的历史任务补齐 owner_open_id。
        避免把其它设备/测试遗留任务错误认领到当前账号。
        """
        open_id = self._effective_owner_open_id()
        if not open_id:
            return False
        if record.owner_open_id not in {None, ""}:
            return False
        if not self._is_local_migratable_path(record.local_path):
            return False
        record.owner_open_id = open_id
        record.updated_at = time.time()
        return True

    @staticmethod
    def _is_local_migratable_path(local_path: str) -> bool:
        normalized = (local_path or "").replace("\\", "/").lower()
        if "pytest-of-" in normalized:
            return False
        if "/appdata/local/temp/" in normalized or normalized.startswith("/tmp/"):
            return False
        try:
            return Path(local_path).expanduser().exists()
        except Exception:
            return False

    @staticmethod
    def _normalize_delete_policy(value: str | None) -> str:
        if not value:
            return DeletePolicy.safe.value
        try:
            return DeletePolicy(str(value)).value
        except ValueError:
            return DeletePolicy.safe.value

    @staticmethod
    def _normalize_md_sync_mode(value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized in _MD_SYNC_MODE_VALUES:
            return normalized
        return _MD_SYNC_MODE_ENHANCED

    def _resolve_task_delete_settings(
        self,
        *,
        delete_policy: str | None,
        delete_grace_minutes: int | None,
    ) -> tuple[str, int]:
        config = ConfigManager.get().config
        policy = self._normalize_delete_policy(
            delete_policy if delete_policy is not None else config.delete_policy.value
        )
        if delete_grace_minutes is None:
            grace = int(config.delete_grace_minutes or 0)
        else:
            grace = int(delete_grace_minutes)
        if grace < 0:
            grace = 0
        if policy == DeletePolicy.strict.value:
            grace = 0
        return policy, grace

    @staticmethod
    def _parse_ignored_subpaths(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        parsed: list[str] = []
        for item in payload:
            if not isinstance(item, str):
                continue
            cleaned = item.strip().replace("\\", "/").strip("/")
            if cleaned:
                parsed.append(cleaned)
        return parsed

    @staticmethod
    def _serialize_ignored_subpaths(value: list[str]) -> str | None:
        if not value:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _normalize_relative_subpath(value: str) -> str:
        normalized_parts: list[str] = []
        for part in Path(value).parts:
            cleaned = str(part).strip().replace("\\", "/")
            if not cleaned or cleaned == ".":
                continue
            if cleaned == "..":
                raise SyncTaskValidationError("忽略目录不能超出本地同步目录")
            if ":" in cleaned:
                raise SyncTaskValidationError("忽略目录必须位于本地同步目录内")
            normalized_parts.append(cleaned)
        if not normalized_parts:
            raise SyncTaskValidationError("忽略目录必须是本地同步目录下的子目录")
        return "/".join(normalized_parts)

    def _normalize_ignored_subpaths(
        self,
        local_path: str,
        ignored_subpaths: list[str] | None,
    ) -> list[str]:
        if not ignored_subpaths:
            return []
        root = Path(local_path).expanduser().resolve(strict=False)
        normalized: list[str] = []
        normalized_keys: list[str] = []
        for raw_value in ignored_subpaths:
            cleaned = (raw_value or "").strip()
            if not cleaned:
                continue
            candidate = Path(cleaned).expanduser()
            if candidate.is_absolute():
                candidate = candidate.resolve(strict=False)
                try:
                    relative = candidate.relative_to(root)
                except ValueError as exc:
                    raise SyncTaskValidationError("忽略目录必须位于本地同步目录内") from exc
            else:
                relative = candidate
            relative_path = self._normalize_relative_subpath(str(relative))
            relative_key = relative_path.lower()
            if any(
                relative_key == existing or relative_key.startswith(f"{existing}/")
                for existing in normalized_keys
            ):
                continue
            keep_indices = [
                index
                for index, existing in enumerate(normalized_keys)
                if not existing.startswith(f"{relative_key}/")
            ]
            normalized = [normalized[index] for index in keep_indices]
            normalized_keys = [normalized_keys[index] for index in keep_indices]
            normalized.append(relative_path)
            normalized_keys.append(relative_key)
        return normalized

    async def _validate_task_mapping(
        self,
        *,
        session: AsyncSession,
        local_path: str,
        cloud_folder_token: str,
        cloud_folder_name: str | None,
        exclude_task_id: str | None,
    ) -> None:
        target_local_key = self._normalize_local_path_for_compare(local_path)
        target_cloud_key = self._normalize_cloud_folder_token(cloud_folder_token)
        target_cloud_path = self._normalize_cloud_folder_path(cloud_folder_name)

        stmt = select(SyncTask).where(SyncTask.owner_device_id == self._owner_device_id)
        open_id = self._effective_owner_open_id()
        if open_id:
            stmt = stmt.where(
                or_(
                    SyncTask.owner_open_id == open_id,
                    SyncTask.owner_open_id.is_(None),
                    SyncTask.owner_open_id == "",
                )
            )
        result = await session.execute(stmt)
        records = result.scalars().all()
        for record in records:
            if exclude_task_id and record.id == exclude_task_id:
                continue
            record_local_key = self._normalize_local_path_for_compare(record.local_path)
            record_cloud_key = self._normalize_cloud_folder_token(record.cloud_folder_token)
            record_cloud_path = self._normalize_cloud_folder_path(record.cloud_folder_name)

            if (
                record_local_key == target_local_key
                and record_cloud_key == target_cloud_key
            ):
                raise SyncTaskValidationError(
                    f"任务已存在：本地目录与云端目录已绑定（任务ID: {record.id}）"
                )
            if (
                record_local_key == target_local_key
                and record_cloud_key != target_cloud_key
            ):
                raise SyncTaskValidationError(
                    "该本地目录已绑定其它云端目录，请先修改或删除原任务"
                )
            if (
                record_cloud_key == target_cloud_key
                and record_local_key != target_local_key
            ):
                raise SyncTaskValidationError(
                    "该云端目录已绑定其它本地目录，请先修改或删除原任务"
                )
            if self._paths_have_containment(record_local_key, target_local_key):
                raise SyncTaskValidationError(
                    "本地目录与现有任务存在包含关系，请避免父子目录同时建任务"
                )
            if self._cloud_paths_have_containment(record_cloud_path, target_cloud_path):
                raise SyncTaskValidationError(
                    "云端目录与现有任务存在包含关系，请避免父子目录同时建任务"
                )

    @staticmethod
    def _clean_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _clean_required_text(
        value: str,
        *,
        field_name: str,
        normalize: bool,
    ) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise SyncTaskValidationError(f"{field_name}不能为空")
        if normalize:
            return cleaned.lower()
        return cleaned

    @staticmethod
    def _normalize_cloud_folder_token(cloud_folder_token: str) -> str:
        return SyncTaskService._clean_required_text(
            cloud_folder_token,
            field_name="云端目录 Token",
            normalize=False,
        )

    @staticmethod
    def _normalize_local_path_for_compare(local_path: str) -> str:
        normalized = str(Path(local_path).expanduser())
        try:
            normalized = str(Path(local_path).expanduser().resolve(strict=False))
        except Exception:
            pass
        normalized = normalized.replace("\\", "/").rstrip("/")
        if len(normalized) == 2 and normalized[1] == ":":
            normalized = f"{normalized}/"
        return normalized.lower()

    @staticmethod
    def _paths_have_containment(left: str, right: str) -> bool:
        if not left or not right or left == right:
            return False
        return left.startswith(f"{right}/") or right.startswith(f"{left}/")

    @staticmethod
    def _normalize_cloud_folder_path(cloud_folder_name: str | None) -> tuple[str, ...]:
        if not cloud_folder_name:
            return ()
        parts = [
            segment.strip().lower()
            for segment in cloud_folder_name.replace("\\", "/").split("/")
            if segment.strip()
        ]
        return tuple(parts)

    @staticmethod
    def _cloud_paths_have_containment(
        left: tuple[str, ...], right: tuple[str, ...]
    ) -> bool:
        if not left or not right or left == right:
            return False
        if len(left) < len(right):
            return right[: len(left)] == left
        return left[: len(right)] == right

    def _to_item(self, record: SyncTask) -> SyncTaskItem:
        config = ConfigManager.get().config
        resolved_md_sync_mode = self._normalize_md_sync_mode(record.md_sync_mode)
        if not (record.md_sync_mode or "").strip():
            resolved_md_sync_mode = (
                _MD_SYNC_MODE_ENHANCED
                if bool(config.upload_md_to_cloud)
                else _MD_SYNC_MODE_DOWNLOAD_ONLY
            )
        resolved_policy = self._normalize_delete_policy(
            record.delete_policy if record.delete_policy is not None else config.delete_policy.value
        )
        if record.delete_grace_minutes is None:
            resolved_grace = int(config.delete_grace_minutes or 0)
        else:
            resolved_grace = int(record.delete_grace_minutes)
        if resolved_grace < 0:
            resolved_grace = 0
        if resolved_policy == DeletePolicy.strict.value:
            resolved_grace = 0
        ignored_subpaths = self._parse_ignored_subpaths(record.ignored_subpaths)
        return SyncTaskItem(
            id=record.id,
            name=record.name,
            local_path=record.local_path,
            cloud_folder_token=record.cloud_folder_token,
            cloud_folder_name=record.cloud_folder_name,
            base_path=record.base_path,
            sync_mode=record.sync_mode,
            update_mode=record.update_mode,
            md_sync_mode=resolved_md_sync_mode,
            ignored_subpaths=ignored_subpaths,
            delete_policy=resolved_policy,
            delete_grace_minutes=resolved_grace,
            is_test=bool(record.is_test),
            enabled=record.enabled,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_run_at=record.last_run_at,
            owner_device_id=record.owner_device_id,
            owner_open_id=record.owner_open_id,
        )


__all__ = ["SyncTaskItem", "SyncTaskService", "SyncTaskValidationError"]
