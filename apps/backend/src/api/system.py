from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
