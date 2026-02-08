from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

from src.api.watcher import watcher_manager
from src.db.session import dispose_engines

router = APIRouter(prefix="/system", tags=["system"])


class FolderResponse(BaseModel):
    path: str


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


@router.post("/select-folder", response_model=FolderResponse)
async def select_folder() -> FolderResponse:
    try:
        path = _select_folder()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not path:
        raise HTTPException(status_code=400, detail="未选择文件夹")
    return FolderResponse(path=path)


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
