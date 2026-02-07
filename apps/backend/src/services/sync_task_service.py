from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import SyncTask
from src.db.session import get_session_maker


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


class SyncTaskService:
    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

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
        enabled: bool = True,
    ) -> SyncTaskItem:
        now = time.time()
        record = SyncTask(
            id=str(uuid.uuid4()),
            name=name,
            local_path=local_path,
            cloud_folder_token=cloud_folder_token,
            cloud_folder_name=cloud_folder_name,
            base_path=base_path,
            sync_mode=sync_mode,
            update_mode=update_mode,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
        async with self._session_maker() as session:
            session.add(record)
            await session.commit()
        return self._to_item(record)

    async def list_tasks(self) -> list[SyncTaskItem]:
        stmt = select(SyncTask).order_by(SyncTask.created_at.desc())
        async with self._session_maker() as session:
            result = await session.execute(stmt)
            records = result.scalars().all()
        return [self._to_item(record) for record in records]

    async def get_task(self, task_id: str) -> SyncTaskItem | None:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return None
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
        enabled: bool | None = None,
    ) -> SyncTaskItem | None:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return None
            if name is not None:
                record.name = name
            if local_path is not None:
                record.local_path = local_path
            if cloud_folder_token is not None:
                record.cloud_folder_token = cloud_folder_token
            if cloud_folder_name is not None:
                record.cloud_folder_name = cloud_folder_name
            if base_path is not None:
                record.base_path = base_path
            if sync_mode is not None:
                record.sync_mode = sync_mode
            if update_mode is not None:
                record.update_mode = update_mode
            if enabled is not None:
                record.enabled = enabled
            record.updated_at = time.time()
            await session.commit()
            return self._to_item(record)

    async def delete_task(self, task_id: str) -> bool:
        async with self._session_maker() as session:
            record = await session.get(SyncTask, task_id)
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True

    @staticmethod
    def _to_item(record: SyncTask) -> SyncTaskItem:
        return SyncTaskItem(
            id=record.id,
            name=record.name,
            local_path=record.local_path,
            cloud_folder_token=record.cloud_folder_token,
            cloud_folder_name=record.cloud_folder_name,
            base_path=record.base_path,
            sync_mode=record.sync_mode,
            update_mode=record.update_mode,
            enabled=record.enabled,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


__all__ = ["SyncTaskItem", "SyncTaskService"]
