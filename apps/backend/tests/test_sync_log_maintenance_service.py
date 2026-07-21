import asyncio
import time
from types import SimpleNamespace

import pytest

from src.services.sync_log_maintenance_service import SyncLogMaintenanceService
from src.services.sync_run_event_service import SyncRunEventBackfillResult


@pytest.mark.asyncio
async def test_sync_log_maintenance_service_runs_backfill_and_prune() -> None:
    class FakeRunEventService:
        def __init__(self) -> None:
            self.backfill_calls = 0
            self.prune_calls: list[int] = []

        async def backfill_step_from_event_store(self, event_store, *, batch_size: int = 200):
            self.backfill_calls += 1
            return SyncRunEventBackfillResult(
                inserted=2,
                skipped=0,
                completed=True,
                offset=128,
                file_size=128,
            )

        async def prune(self, *, retention_days: int, min_interval_seconds: int = 0):
            self.prune_calls.append(retention_days)
            return 3

    class FakeEventStore:
        def __init__(self) -> None:
            self.prune_calls: list[int] = []

        def prune(self, *, retention_days: int, min_interval_seconds: int = 0):
            self.prune_calls.append(retention_days)
            return 2

    config_manager = SimpleNamespace(
        config=SimpleNamespace(sync_log_retention_days=7)
    )
    run_event_service = FakeRunEventService()
    event_store = FakeEventStore()
    service = SyncLogMaintenanceService(
        run_event_service=run_event_service,
        event_store=event_store,
        config_manager=config_manager,
    )

    tick = await service.run_once()

    assert tick.backfill.inserted == 2
    assert tick.pruned_db_events == 3
    assert tick.pruned_jsonl_events == 2
    assert run_event_service.backfill_calls == 1
    assert run_event_service.prune_calls == [7]
    assert event_store.prune_calls == [7]


@pytest.mark.asyncio
async def test_jsonl_prune_does_not_block_the_event_loop() -> None:
    class FakeRunEventService:
        async def backfill_step_from_event_store(self, event_store, *, batch_size: int = 200):
            return SyncRunEventBackfillResult(0, 0, True, 0, 0)

        async def prune(self, *, retention_days: int, min_interval_seconds: int = 0):
            return 0

    class SlowEventStore:
        def prune(self, *, retention_days: int, min_interval_seconds: int = 0):
            time.sleep(0.05)
            return 0

    service = SyncLogMaintenanceService(
        run_event_service=FakeRunEventService(),
        event_store=SlowEventStore(),
        config_manager=SimpleNamespace(config=SimpleNamespace(sync_log_retention_days=7)),
    )

    task = asyncio.create_task(service.run_once())
    await asyncio.sleep(0.005)
    assert not task.done()
    await task
