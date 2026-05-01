from src.api.sync_tasks import SyncTaskUpdateRequest, _task_update_requires_restart


def test_task_update_requires_restart_for_ignored_subpaths() -> None:
    payload = SyncTaskUpdateRequest(ignored_subpaths=["POC/GENESIS"])
    assert _task_update_requires_restart(payload) is True


def test_task_update_does_not_require_restart_for_name_only() -> None:
    payload = SyncTaskUpdateRequest(name="新名称")
    assert _task_update_requires_restart(payload) is False
