import pytest

from src.db.session import get_session_maker, init_db
from src.services.sync_link_service import SyncLinkService


@pytest.mark.asyncio
async def test_upsert_and_get_link(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = SyncLinkService(session_maker=get_session_maker(db_url))

    item = await service.upsert_link(
        local_path="C:/docs/a.md",
        cloud_token="doccn123",
        cloud_type="docx",
        task_id="task-1",
        updated_at=123.0,
    )
    assert item.cloud_token == "doccn123"

    fetched = await service.get_by_local_path("C:/docs/a.md")
    assert fetched is not None
    assert fetched.cloud_type == "docx"

    await service.upsert_link(
        local_path="C:/docs/a.md",
        cloud_token="doccn456",
        cloud_type="docx",
        task_id="task-1",
        updated_at=456.0,
    )

    updated = await service.get_by_local_path("C:/docs/a.md")
    assert updated is not None
    assert updated.cloud_token == "doccn456"
    assert updated.updated_at == 456.0
