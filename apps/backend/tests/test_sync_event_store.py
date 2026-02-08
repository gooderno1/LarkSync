from pathlib import Path

from src.services.sync_event_store import SyncEventRecord, SyncEventStore


def test_sync_event_store_persists_and_filters(tmp_path: Path) -> None:
    log_file = tmp_path / "sync-events.jsonl"
    store = SyncEventStore(log_file)

    store.append(
        SyncEventRecord(
            timestamp=1.0,
            task_id="task-1",
            task_name="同步任务A",
            status="downloaded",
            path="/tmp/a.md",
            message="ok",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=2.0,
            task_id="task-1",
            task_name="同步任务A",
            status="failed",
            path="/tmp/b.md",
            message="boom",
        )
    )
    store.append(
        SyncEventRecord(
            timestamp=3.0,
            task_id="task-2",
            task_name="同步任务B",
            status="uploaded",
            path="/tmp/c.md",
            message="done",
        )
    )

    total, items = store.read_events(
        limit=10,
        offset=0,
        status="failed",
        search="",
        task_id="",
        order="desc",
    )
    assert total == 1
    assert items[0].status == "failed"

    total, items = store.read_events(
        limit=10,
        offset=0,
        status="",
        search="任务b",
        task_id="",
        order="desc",
    )
    assert total == 1
    assert items[0].task_name == "同步任务B"

    total, items = store.read_events(
        limit=10,
        offset=0,
        status="",
        search="boom",
        task_id="task-1",
        order="desc",
    )
    assert total == 1
    assert items[0].path == "/tmp/b.md"


def test_sync_event_store_order_and_pagination(tmp_path: Path) -> None:
    log_file = tmp_path / "sync-events.jsonl"
    store = SyncEventStore(log_file)

    for idx in range(5):
        store.append(
            SyncEventRecord(
                timestamp=float(idx),
                task_id="task-1",
                task_name="任务",
                status="downloaded",
                path=f"/tmp/{idx}.md",
                message=None,
            )
        )

    total, items = store.read_events(
        limit=2,
        offset=0,
        status="",
        search="",
        task_id="",
        order="asc",
    )
    assert total == 5
    assert [item.timestamp for item in items] == [0.0, 1.0]

    total, items = store.read_events(
        limit=2,
        offset=0,
        status="",
        search="",
        task_id="",
        order="desc",
    )
    assert [item.timestamp for item in items] == [4.0, 3.0]

    total, items = store.read_events(
        limit=1,
        offset=1,
        status="",
        search="",
        task_id="",
        order="desc",
    )
    assert [item.timestamp for item in items] == [3.0]

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")

    total, items = store.read_events(
        limit=10,
        offset=0,
        status="",
        search="",
        task_id="",
        order="asc",
    )
    assert total == 5
    assert len(items) == 5
