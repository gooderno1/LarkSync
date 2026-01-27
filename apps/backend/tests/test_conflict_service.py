from src.services.conflict_service import ConflictService


def test_detects_conflict_when_hash_and_version_diverge() -> None:
    service = ConflictService()
    item = service.detect_and_add(
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


def test_no_conflict_when_versions_not_greater() -> None:
    service = ConflictService()
    item = service.detect_and_add(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=1,
        db_version=1,
    )
    assert item is None


def test_resolve_conflict_marks_action() -> None:
    service = ConflictService()
    item = service.add_conflict(
        local_path="C:/docs/a.md",
        cloud_token="docx123",
        local_hash="hash-local",
        db_hash="hash-db",
        cloud_version=3,
        db_version=1,
    )
    resolved = service.resolve(item.id, "use_local")
    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.resolved_action == "use_local"
