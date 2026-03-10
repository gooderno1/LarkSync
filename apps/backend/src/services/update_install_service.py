from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel

from src.core.paths import data_dir


class UpdateInstallRequest(BaseModel):
    installer_path: str
    created_at: float


def install_request_path() -> Path:
    return data_dir() / "updates" / "install-request.json"


def queue_install_request(
    installer_path: str | Path,
    *,
    created_at: float | None = None,
) -> UpdateInstallRequest:
    path = Path(installer_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"安装包不存在: {path}")

    request = UpdateInstallRequest(
        installer_path=str(path),
        created_at=float(created_at if created_at is not None else time.time()),
    )
    request_path = install_request_path()
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(request.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return request


def load_install_request() -> UpdateInstallRequest | None:
    path = install_request_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return UpdateInstallRequest.model_validate(payload)


def clear_install_request() -> None:
    install_request_path().unlink(missing_ok=True)


__all__ = [
    "UpdateInstallRequest",
    "clear_install_request",
    "install_request_path",
    "load_install_request",
    "queue_install_request",
]
