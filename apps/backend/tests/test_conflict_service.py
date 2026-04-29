import pytest

from src.db.session import get_session_maker, init_db
from src.services.conflict_service import ConflictService


@pytest.mark.asyncio
async def test_detects_conflict_when_hash_and_version_diverge(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = ConflictService(session_maker=get_session_maker(db_url))

    item = await service.detect_and_add(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=2,
        db_version=1,
        local_preview="local",
        cloud_preview="cloud",
    )
    assert item is not None
    assert item.local_path == "C:/docs/a.md"


@pytest.mark.asyncio
async def test_no_conflict_when_versions_not_greater(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = ConflictService(session_maker=get_session_maker(db_url))

    item = await service.detect_and_add(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=1,
        db_version=1,
    )
    assert item is None


@pytest.mark.asyncio
async def test_resolve_conflict_marks_action(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = ConflictService(session_maker=get_session_maker(db_url))

    item = await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    resolved = await service.resolve(item.id, "use_local")
    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.resolved_action == "use_local"


@pytest.mark.asyncio
async def test_add_conflict_reuses_same_unresolved_conflict(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = ConflictService(session_maker=get_session_maker(db_url))

    first = await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
        local_preview="local",
        cloud_preview="cloud",
    )
    second = await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
        local_preview="local",
        cloud_preview="cloud",
    )

    conflicts = await service.list_conflicts()
    assert first.id == second.id
    assert len(conflicts) == 1


@pytest.mark.asyncio
async def test_list_conflicts_deduplicates_existing_duplicate_records(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    await init_db(db_url)
    service = ConflictService(session_maker=get_session_maker(db_url))

    first = await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    await service.resolve(first.id, "use_cloud")
    await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    duplicate = await service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )

    unresolved = await service.list_conflicts()
    all_conflicts = await service.list_conflicts(include_resolved=True)

    assert len(unresolved) == 1
    assert unresolved[0].id == duplicate.id
    assert len(all_conflicts) == 2
