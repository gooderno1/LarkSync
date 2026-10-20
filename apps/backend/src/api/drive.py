from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services.auth_service import AuthError
from src.services.drive_service import DriveFileList, DriveNode, DriveService

router = APIRouter(prefix="/drive", tags=["drive"])


@router.get("/files", response_model=DriveFileList)
async def list_drive_files(
    folder_token: str | None = Query(default=None),
    page_token: str | None = Query(default=None),
    page_size: int = Query(default=100, ge=1, le=200),
) -> DriveFileList:
    """Browse one page without recursively scanning the account."""
    service = DriveService()
    try:
        token = folder_token or (await service.get_root_folder_meta()).token
        return await service.list_files(token, page_token=page_token, page_size=page_size)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await service.close()


@router.get("/tree", response_model=DriveNode)
async def get_drive_tree(
    folder_token: str | None = Query(default=None),
    name: str | None = Query(default=None),
) -> DriveNode:
    service = DriveService()
    try:
        if folder_token:
            return await service.scan_folder(folder_token, name=name or folder_token)
        return await service.scan_roots()
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await service.close()
