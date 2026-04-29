from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import ConflictRecord
from src.db.session import get_session_maker


@dataclass
class ConflictItem:
    id: str
    local_path: str
    cloud_token: str
    local_hash: str
    db_hash: str
    cloud_version: int
    db_version: int
    local_preview: str | None
    cloud_preview: str | None
    created_at: float
    resolved: bool = False
    resolved_action: str | None = None


class ConflictService:
    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._session_maker = session_maker or get_session_maker()

    async def detect_and_add(
        self,
        *,
        local_path: str,
        cloud_token: str,
        local_hash: str,
        db_hash: str,
        cloud_version: int,
        db_version: int,
        local_preview: str | None = None,
        cloud_preview: str | None = None,
    ) -> ConflictItem | None:
        if local_hash != db_hash and cloud_version > db_version:
            return await self.add_conflict(
                local_path=local_path,
                cloud_token=cloud_token,
                local_hash=local_hash,
                db_hash=db_hash,
                cloud_version=cloud_version,
                db_version=db_version,
                local_preview=local_preview,
                cloud_preview=cloud_preview,
            )
        return None

    async def add_conflict(
        self,
        *,
        local_path: str,
        cloud_token: str,
        local_hash: str,
        db_hash: str,
        cloud_version: int,
        db_version: int,
        local_preview: str | None = None,
        cloud_preview: str | None = None,
    ) -> ConflictItem:
        async with self._session_maker() as session:
            record = await self._find_matching_unresolved_conflict(
                session,
                local_path=local_path,
                cloud_token=cloud_token,
                local_hash=local_hash,
                db_hash=db_hash,
                cloud_version=cloud_version,
                db_version=db_version,
            )
            if record:
                if local_preview is not None:
                    record.local_preview = local_preview
                if cloud_preview is not None:
                    record.cloud_preview = cloud_preview
                await session.commit()
                await session.refresh(record)
                return self._to_item(record)

            record = ConflictRecord(
                id=str(uuid.uuid4()),
                local_path=local_path,
                cloud_token=cloud_token,
                local_hash=local_hash,
                db_hash=db_hash,
                cloud_version=cloud_version,
                db_version=db_version,
                local_preview=local_preview,
                cloud_preview=cloud_preview,
                created_at=time.time(),
                resolved=False,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return self._to_item(record)

    async def list_conflicts(self, include_resolved: bool = False) -> list[ConflictItem]:
        stmt = select(ConflictRecord)
        if not include_resolved:
            stmt = stmt.where(ConflictRecord.resolved.is_(False))
        stmt = stmt.order_by(ConflictRecord.created_at.desc())
        async with self._session_maker() as session:
            result = await session.execute(stmt)
            records = result.scalars().all()
        visible_records: list[ConflictRecord] = []
        seen_unresolved_keys: set[tuple[str, str, str, str, int, int]] = set()
        for record in records:
            if record.resolved:
                visible_records.append(record)
                continue
            key = self._conflict_signature(record)
            if key in seen_unresolved_keys:
                continue
            seen_unresolved_keys.add(key)
            visible_records.append(record)
        return [self._to_item(record) for record in visible_records]

    async def resolve(self, conflict_id: str, action: str) -> ConflictItem | None:
        async with self._session_maker() as session:
            record = await session.get(ConflictRecord, conflict_id)
            if not record:
                return None
            record.resolved = True
            record.resolved_action = action
            record.resolved_at = time.time()
            await session.commit()
            return self._to_item(record)

    @staticmethod
    def _to_item(record: ConflictRecord) -> ConflictItem:
        return ConflictItem(
            id=record.id,
            local_path=record.local_path,
            cloud_token=record.cloud_token,
            local_hash=record.local_hash,
            db_hash=record.db_hash,
            cloud_version=record.cloud_version,
            db_version=record.db_version,
            local_preview=record.local_preview,
            cloud_preview=record.cloud_preview,
            created_at=record.created_at,
            resolved=record.resolved,
            resolved_action=record.resolved_action,
        )

    async def _find_matching_unresolved_conflict(
        self,
        session: AsyncSession,
        *,
        local_path: str,
        cloud_token: str,
        local_hash: str,
        db_hash: str,
        cloud_version: int,
        db_version: int,
    ) -> ConflictRecord | None:
        stmt = (
            select(ConflictRecord)
            .where(ConflictRecord.resolved.is_(False))
            .where(ConflictRecord.local_path == local_path)
            .where(ConflictRecord.cloud_token == cloud_token)
            .where(ConflictRecord.local_hash == local_hash)
            .where(ConflictRecord.db_hash == db_hash)
            .where(ConflictRecord.cloud_version == cloud_version)
            .where(ConflictRecord.db_version == db_version)
            .order_by(ConflictRecord.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _conflict_signature(
        record: ConflictRecord,
    ) -> tuple[str, str, str, str, int, int]:
        return (
            record.local_path,
            record.cloud_token,
            record.local_hash,
            record.db_hash,
            record.cloud_version,
            record.db_version,
        )
