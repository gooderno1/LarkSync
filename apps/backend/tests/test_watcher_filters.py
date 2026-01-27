from src.services.watcher import DebounceFilter, IgnoreRegistry


def test_debounce_filter() -> None:
    debounce = DebounceFilter(window_seconds=2.0)
    assert debounce.should_emit("file.txt", now=0.0)
    assert not debounce.should_emit("file.txt", now=1.0)
    assert debounce.should_emit("file.txt", now=3.0)


def test_ignore_registry() -> None:
    ignore = IgnoreRegistry(ttl_seconds=2.0)
    ignore.add("file.txt", now=0.0)
    assert ignore.is_ignored("file.txt", now=1.0)
    assert not ignore.is_ignored("file.txt", now=3.0)
