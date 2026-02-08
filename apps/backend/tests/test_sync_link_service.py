import pytest
from sqlalchemy.exc import DatabaseError

from src.services.sync_link_service import SyncLinkService


class BrokenSession:
    def __init__(self) -> None:
        self._error = DatabaseError("stmt", {}, Exception("db broken"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        raise self._error

    async def execute(self, *args, **kwargs):
        raise self._error

    async def commit(self):
        raise self._error


class BrokenSessionMaker:
    def __call__(self):
        return BrokenSession()


@pytest.mark.asyncio
async def test_sync_link_service_handles_db_errors() -> None:
    service = SyncLinkService(session_maker=BrokenSessionMaker())

    item = await service.upsert_link(
        local_path="/tmp/a.md",
        cloud_token="token",
        cloud_type="docx",
        task_id="task-1",
        updated_at=1.0,
    )
    assert item.local_path == "/tmp/a.md"
    assert item.cloud_token == "token"

    assert await service.get_by_local_path("/tmp/a.md") is None
    assert await service.list_by_task("task-1") == []
    assert await service.list_all() == []
