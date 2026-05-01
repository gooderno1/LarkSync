from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

from src.api.watcher import watcher_manager
from src.db.session import dispose_engines
from src.services.update_install_service import queue_install_request
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
    pass


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


def _open_directory_in_file_manager(path: Path) -> None:
    target = path.resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"目录不存在: {target}")
    if sys.platform == "win32":
        os.startfile(str(target))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", str(target)], close_fds=True)
        return
    subprocess.Popen(["xdg-open", str(target)], close_fds=True)


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


@router.post("/select-folder", response_model=FolderResponse)
async def select_folder() -> FolderResponse:
    try:
        path = _select_folder()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not path:
        raise HTTPException(status_code=400, detail="未选择文件夹")
    return FolderResponse(path=path)


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
    return UpdateStatusResponse.model_validate(status.model_dump())


@router.post("/update/check", response_model=UpdateStatusResponse)
async def update_check(request: Request) -> UpdateStatusResponse:
    service = _get_update_service(request)
    status = await service.check_for_updates(force=True)
    return UpdateStatusResponse.model_validate(status.model_dump())


@router.post("/update/download", response_model=UpdateStatusResponse)
async def update_download(request: Request) -> UpdateStatusResponse:
    service = _get_update_service(request)
    try:
        status = await service.download_update()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UpdateStatusResponse.model_validate(status.model_dump())


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
    if runner is not None:
        try:
            for task_id in list(runner.list_statuses().keys()):
                runner.cancel_task(task_id)
        except Exception as exc:
            logger.warning("停止同步任务失败: {}", exc)
    scheduler = getattr(app.state, "sync_scheduler", None)
    if scheduler is not None:
        try:
            await scheduler.stop()
        except Exception as exc:
            logger.warning("停止同步调度器失败: {}", exc)
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
