from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

import src.api.drive as drive_api
import src.api.sync_tasks as tasks_api
from src.services.drive_service import DriveFileList


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get_task_status", "delete_task", "get_task"])
async def test_cross_account_task_is_rejected_before_runner_access(monkeypatch, operation):
    monkeypatch.setattr(tasks_api.service, "get_task", AsyncMock(return_value=None))
    cancel = Mock()
    status = Mock()
    monkeypatch.setattr(tasks_api.runner, "cancel_task", cancel)
    monkeypatch.setattr(tasks_api.runner, "get_status", status)
    with pytest.raises(HTTPException) as caught:
        await getattr(tasks_api, operation)("other-account-task")
    assert caught.value.status_code == 404
    cancel.assert_not_called()
    status.assert_not_called()


@pytest.mark.asyncio
async def test_drive_browse_only_lists_requested_page_and_closes(monkeypatch):
    page = DriveFileList(files=[], has_more=True, next_page_token="next")
    service = SimpleNamespace(
        list_files=AsyncMock(return_value=page),
        get_root_folder_meta=AsyncMock(return_value=SimpleNamespace(token="root")),
        close=AsyncMock(),
    )
    monkeypatch.setattr(drive_api, "DriveService", lambda: service)
    result = await drive_api.list_drive_files(folder_token=None, page_token="cursor", page_size=20)
    assert result == page
    service.list_files.assert_awaited_once_with("root", page_token="cursor", page_size=20)
    service.close.assert_awaited_once()
