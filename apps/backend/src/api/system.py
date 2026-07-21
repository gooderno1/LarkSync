from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

from src.api.watcher import watcher_manager
from src.core.config import ConfigManager
from src.core.device import current_device_id
from src.core.file_manager import open_directory_in_file_manager as _open_directory_in_file_manager
from src.core.paths import data_dir, bundle_root
from src.db.session import dispose_engines
from src.services import AuthService
from src.services.update_install_service import (
    UpdateInstallHandoff,
    UpdateInstallRequest,
    load_install_handoff,
    load_install_request,
    queue_install_request,
)
from src.services.update_service import (
    UpdateService,
    UpdateStatus,
    extract_installer_version,
    is_newer_version,
)
from src.services.update_scheduler import UpdateScheduler
from src.core.version import get_version

router = APIRouter(prefix="/system", tags=["system"])


class FolderResponse(BaseModel):
    path: str


class UpdateStatusResponse(UpdateStatus):
    install_request: UpdateInstallRequest | None = None
    install_handoff: UpdateInstallHandoff | None = None


class UpdateInstallPayload(BaseModel):
    download_path: str | None = None
    silent: bool = True


class UpdateInstallResponse(BaseModel):
    queued: bool
    installer_path: str
    silent: bool
    restart_path: str | None = None


class UpdateOpenFolderPayload(BaseModel):
    download_path: str | None = None


class DesktopRuntimeStatus(BaseModel):
    backend_running: bool
    frontend_static_available: bool
    data_dir: str
    database_url: str
    packaged: bool
    profile: str
    cloud_write_policy: str
    scheduler_disabled: bool
    watcher_disabled: bool


class DesktopAuthStatus(BaseModel):
    connected: bool
    oauth_configured: bool
    open_id: str | None = None
    account_name: str | None = None
    device_id: str
    expires_at: float | None = None


class DesktopTaskStatus(BaseModel):
    total: int
    enabled: int
    paused: int
    running: int
    failed: int
    last_error: str | None = None
    last_sync_time: float | None = None


class DesktopConflictStatus(BaseModel):
    unresolved: int


class DesktopUpdateStatus(BaseModel):
    current_version: str
    latest_version: str | None = None
    update_available: bool = False
    last_check: float | None = None
    last_error: str | None = None
    download_path: str | None = None


class DesktopStatusResponse(BaseModel):
    runtime: DesktopRuntimeStatus
    auth: DesktopAuthStatus
    tasks: DesktopTaskStatus
    conflicts: DesktopConflictStatus
    update: DesktopUpdateStatus


class TrayStatusResponse(BaseModel):
    backend_running: bool
    tasks_total: int
    tasks_running: int
    tasks_paused: int
    unresolved_conflicts: int
    last_error: str | None = None
    last_sync_time: float | None = None


def _select_folder() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # pragma: no cover - defensive for missing tkinter
        raise RuntimeError("无法打开系统文件夹选择器，请确认 tkinter 可用") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        path = filedialog.askdirectory()
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return path or None


def _resolve_download_directory(service: UpdateService, raw_path: str | None) -> Path:
    download_path = (raw_path or "").strip()
    if not download_path:
        cached = service.load_cached_status()
        download_path = (cached.download_path or "").strip()
    if not download_path:
        raise FileNotFoundError("尚未下载更新包")
    installer_path = Path(download_path).expanduser().resolve()
    if not installer_path.exists():
        raise FileNotFoundError(f"安装包不存在: {installer_path}")
    return installer_path.parent


def _frontend_dist_available() -> bool:
    root = bundle_root() or Path(__file__).resolve().parents[3]
    return (root / "apps" / "frontend" / "dist" / "index.html").exists()


def _runtime_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


async def build_desktop_status(request: Request) -> DesktopStatusResponse:
    config = ConfigManager.get().config
    runner = getattr(request.app.state, "sync_runner", None)
    task_service = getattr(request.app.state, "sync_task_service", None)
    conflict_service = getattr(request.app.state, "conflict_service", None)

    statuses = runner.list_statuses() if runner is not None else {}
    tasks = await task_service.list_tasks() if task_service is not None else []
    enabled_task_ids = {task.id for task in tasks if task.enabled}
    conflicts = (
        await conflict_service.list_conflicts(include_resolved=False)
        if conflict_service is not None
        else []
    )
    errors = [status.last_error for status in statuses.values() if status.last_error]
    last_sync = max(
        (status.finished_at for status in statuses.values() if status.finished_at),
        default=None,
    )
    try:
        token = await asyncio.to_thread(AuthService().get_cached_token)
    except Exception as exc:
        logger.debug("读取桌面状态 token 缓存失败: {}", exc)
        token = None
    update_status = _get_update_service(request).load_cached_status()

    return DesktopStatusResponse(
        runtime=DesktopRuntimeStatus(
            backend_running=True,
            frontend_static_available=_frontend_dist_available(),
            data_dir=str(data_dir()),
            database_url=config.database_url,
            packaged=_runtime_packaged(),
            profile=config.runtime_profile.value,
            cloud_write_policy=config.effective_cloud_write_policy.value,
            scheduler_disabled=config.effective_disable_scheduler,
            watcher_disabled=config.effective_disable_watcher,
        ),
        auth=DesktopAuthStatus(
            connected=token is not None,
            oauth_configured=bool(config.auth_client_id.strip()),
            open_id=token.open_id if token else None,
            account_name=token.account_name if token else None,
            device_id=current_device_id(),
            expires_at=token.expires_at if token else None,
        ),
        tasks=DesktopTaskStatus(
            total=len(tasks),
            enabled=sum(1 for task in tasks if task.enabled),
            paused=sum(1 for task in tasks if not task.enabled),
            running=sum(
                1
                for task_id, status in statuses.items()
                if task_id in enabled_task_ids and status.state == "running"
            ),
            failed=sum(1 for status in statuses.values() if status.state == "failed"),
            last_error=errors[0] if errors else None,
            last_sync_time=last_sync,
        ),
        conflicts=DesktopConflictStatus(unresolved=len(conflicts)),
        update=DesktopUpdateStatus(
            current_version=get_version(),
            latest_version=update_status.latest_version,
            update_available=bool(update_status.update_available),
            last_check=update_status.last_check,
            last_error=update_status.last_error,
            download_path=update_status.download_path,
        ),
    )


def desktop_status_to_tray_status(status: DesktopStatusResponse) -> TrayStatusResponse:
    return TrayStatusResponse(
        backend_running=status.runtime.backend_running,
        tasks_total=status.tasks.total,
        tasks_running=status.tasks.running,
        tasks_paused=status.tasks.paused,
        unresolved_conflicts=status.conflicts.unresolved,
        last_error=status.tasks.last_error,
        last_sync_time=status.tasks.last_sync_time,
    )


@router.post("/select-folder", response_model=FolderResponse)
async def select_folder() -> FolderResponse:
    try:
        path = _select_folder()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not path:
        raise HTTPException(status_code=400, detail="未选择文件夹")
    return FolderResponse(path=path)


@router.get("/desktop/status", response_model=DesktopStatusResponse)
async def desktop_status(request: Request) -> DesktopStatusResponse:
    return await build_desktop_status(request)


def _get_update_service(request: Request) -> UpdateService:
    scheduler: UpdateScheduler | None = getattr(request.app.state, "update_scheduler", None)
    if scheduler is not None:
        return scheduler.service
    service: UpdateService | None = getattr(request.app.state, "update_service", None)
    if service is None:
        service = UpdateService()
        request.app.state.update_service = service
    return service


def _current_restart_path() -> str | None:
    if not getattr(sys, "frozen", False):
        return None
    path = (sys.executable or "").strip()
    return path or None


@router.get("/update/status", response_model=UpdateStatusResponse)
async def update_status(request: Request) -> UpdateStatusResponse:
    service = _get_update_service(request)
    status = service.load_cached_status()
    return UpdateStatusResponse(
        **status.model_dump(),
        install_request=load_install_request(),
        install_handoff=load_install_handoff(),
    )


@router.post("/update/check", response_model=UpdateStatusResponse)
async def update_check(request: Request) -> UpdateStatusResponse:
    service = _get_update_service(request)
    status = await service.check_for_updates(force=True)
    return UpdateStatusResponse(
        **status.model_dump(),
        install_request=load_install_request(),
        install_handoff=load_install_handoff(),
    )


@router.post("/update/download", response_model=UpdateStatusResponse)
async def update_download(request: Request) -> UpdateStatusResponse:
    service = _get_update_service(request)
    try:
        status = await service.download_update()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UpdateStatusResponse(
        **status.model_dump(),
        install_request=load_install_request(),
        install_handoff=load_install_handoff(),
    )


@router.post("/update/install", response_model=UpdateInstallResponse)
async def update_install(
    payload: UpdateInstallPayload,
    request: Request,
) -> UpdateInstallResponse:
    service = _get_update_service(request)
    installer_path = (payload.download_path or "").strip()
    if not installer_path:
        cached = service.load_cached_status()
        installer_path = (cached.download_path or "").strip()
    if not installer_path:
        raise HTTPException(status_code=400, detail="尚未下载更新包")
    installer_version = extract_installer_version(installer_path)
    current_version = get_version()
    if installer_version and not is_newer_version(installer_version, current_version):
        raise HTTPException(
            status_code=400,
            detail=f"当前已是 {current_version}，无需再次安装 {installer_version}",
        )
    try:
        queued = queue_install_request(
            installer_path,
            silent=payload.silent,
            restart_path=_current_restart_path(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UpdateInstallResponse(
        queued=True,
        installer_path=queued.installer_path,
        silent=queued.silent,
        restart_path=queued.restart_path,
    )


@router.post("/update/open-download-folder", response_model=FolderResponse)
async def update_open_download_folder(
    payload: UpdateOpenFolderPayload,
    request: Request,
) -> FolderResponse:
    service = _get_update_service(request)
    try:
        folder = _resolve_download_directory(service, payload.download_path)
        _open_directory_in_file_manager(folder)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"打开目录失败: {exc}") from exc
    return FolderResponse(path=str(folder))


async def _shutdown_after_response(app) -> None:
    logger.info("收到系统关闭请求，准备停止服务")
    runner = getattr(app.state, "sync_runner", None)
    scheduler = getattr(app.state, "sync_scheduler", None)
    if scheduler is not None:
        try:
            await scheduler.stop()
        except Exception as exc:
            logger.warning("停止同步调度器失败: {}", exc)
    if runner is not None:
        close_runner = getattr(runner, "close", None)
        try:
            if callable(close_runner):
                await close_runner()
            else:
                for task_id in list(runner.list_statuses().keys()):
                    runner.cancel_task(task_id)
        except Exception as exc:
            logger.warning("停止同步任务失败: {}", exc)
    try:
        watcher_manager.stop()
    except Exception as exc:
        logger.warning("停止文件监听失败: {}", exc)
    try:
        await dispose_engines()
    except Exception as exc:
        logger.warning("释放数据库连接失败: {}", exc)
    await asyncio.sleep(0.2)
    os._exit(0)


def _schedule_shutdown(app) -> None:
    asyncio.create_task(_shutdown_after_response(app))


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    _schedule_shutdown(request.app)
    return {"status": "shutting_down"}
