from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import SyncMapping


@pytest.mark.asyncio
async def test_sync_mapping_create_and_insert(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        record = SyncMapping(
            file_hash="hash-001",
            feishu_token="token-001",
            local_path="C:/docs/spec.md",
            last_sync_mtime=0.0,
            version=1,
        )
        session.add(record)
        await session.commit()

    async with Session() as session:
        loaded = await session.get(SyncMapping, "hash-001")
        assert loaded is not None
        assert loaded.feishu_token == "token-001"

    assert db_path.exists()
