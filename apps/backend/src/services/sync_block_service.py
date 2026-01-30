from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select

from src.db.models import SyncBlockState
from src.db.session import get_session_maker


@dataclass
class BlockStateItem:
    file_hash: str
    local_path: str
    cloud_token: str
    block_index: int
    block_hash: str
    block_count: int
    updated_at: float
    created_at: float


class SyncBlockService:
    def __init__(self) -> None:
        self._session_maker = get_session_maker()

    async def list_blocks(self, local_path: str, cloud_token: str) -> list[BlockStateItem]:
        async with self._session_maker() as session:
            result = await session.execute(
                select(SyncBlockState)
                .where(SyncBlockState.local_path == local_path)
                .where(SyncBlockState.cloud_token == cloud_token)
                .order_by(SyncBlockState.block_index)
            )
            records = result.scalars().all()
        return [
            BlockStateItem(
                file_hash=record.file_hash,
                local_path=record.local_path,
                cloud_token=record.cloud_token,
                block_index=record.block_index,
                block_hash=record.block_hash,
                block_count=record.block_count,
                updated_at=record.updated_at,
                created_at=record.created_at,
            )
            for record in records
        ]

    async def replace_blocks(
        self, local_path: str, cloud_token: str, items: Iterable[BlockStateItem]
    ) -> None:
        async with self._session_maker() as session:
            await session.execute(
                delete(SyncBlockState)
                .where(SyncBlockState.local_path == local_path)
                .where(SyncBlockState.cloud_token == cloud_token)
            )
            now = time.time()
            for item in items:
                record = SyncBlockState(
                    id=str(uuid.uuid4()),
                    file_hash=item.file_hash,
                    local_path=item.local_path,
                    cloud_token=item.cloud_token,
                    block_index=item.block_index,
                    block_hash=item.block_hash,
                    block_count=item.block_count,
                    updated_at=item.updated_at or now,
                    created_at=item.created_at or now,
                )
                session.add(record)
            await session.commit()


__all__ = ["BlockStateItem", "SyncBlockService"]
