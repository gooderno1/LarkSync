from __future__ import annotations

import pytest

from src.services.watcher import DebounceFilter, FileEventHandler, IgnoreRegistry


class DummyEvent:
    def __init__(
        self,
        src_path: str,
        dest_path: str | None = None,
        event_type: str = "moved",
        is_directory: bool = False,
    ) -> None:
        self.src_path = src_path
        self.dest_path = dest_path
        self.event_type = event_type
        self.is_directory = is_directory


def test_ignore_dest_path_suppresses_event() -> None:
    events = []
    ignore = IgnoreRegistry(ttl_seconds=10.0)
    debounce = DebounceFilter(window_seconds=0.0)
    handler = FileEventHandler(lambda event: events.append(event), debounce, ignore)
    dest_path = "C:\\tmp\\file.md"
    ignore.add(dest_path)
    handler.on_any_event(DummyEvent("C:\\tmp\\tmp123", dest_path=dest_path))
    assert events == []


def test_debounce_uses_dest_path_for_moved_event() -> None:
    events = []
    ignore = IgnoreRegistry(ttl_seconds=10.0)
    debounce = DebounceFilter(window_seconds=10.0)
    handler = FileEventHandler(lambda event: events.append(event), debounce, ignore)
    dest_path = "C:\\tmp\\file.md"
    handler.on_any_event(DummyEvent("C:\\tmp\\tmp1", dest_path=dest_path))
    handler.on_any_event(DummyEvent("C:\\tmp\\tmp2", dest_path=dest_path))
    assert len(events) == 1
    assert events[0].dest_path == dest_path


def test_directory_deleted_event_is_emitted_with_directory_flag() -> None:
    events = []
    ignore = IgnoreRegistry(ttl_seconds=10.0)
    debounce = DebounceFilter(window_seconds=0.0)
    handler = FileEventHandler(lambda event: events.append(event), debounce, ignore)

    handler.on_any_event(
        DummyEvent("C:\\tmp\\folder", event_type="deleted", is_directory=True)
    )

    assert len(events) == 1
    assert events[0].event_type == "deleted"
    assert events[0].src_path == "C:\\tmp\\folder"
    assert events[0].is_directory is True


@pytest.mark.parametrize("event_type", ["opened", "closed", "closed_no_write", "unknown"])
def test_read_only_file_lifecycle_events_are_ignored(event_type: str) -> None:
    events = []
    handler = FileEventHandler(
        lambda event: events.append(event),
        DebounceFilter(window_seconds=0.0),
        IgnoreRegistry(ttl_seconds=10.0),
    )

    handler.on_any_event(DummyEvent("C:\\tmp\\file.md", event_type=event_type))

    assert events == []


@pytest.mark.parametrize("event_type", ["created", "modified", "moved", "deleted"])
def test_mutating_file_events_are_emitted(event_type: str) -> None:
    events = []
    handler = FileEventHandler(
        lambda event: events.append(event),
        DebounceFilter(window_seconds=0.0),
        IgnoreRegistry(ttl_seconds=10.0),
    )

    handler.on_any_event(DummyEvent("C:\\tmp\\file.md", event_type=event_type))

    assert len(events) == 1
    assert events[0].event_type == event_type
