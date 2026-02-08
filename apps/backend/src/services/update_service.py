from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel

from src.core.config import ConfigManager
from src.core.paths import data_dir, logs_dir
from src.core.version import get_version

_VERSION_RE = re.compile("^v?(\\d+)\\.(\\d+)\\.(\\d+)(?:-dev\\.(\\d+))?$")


class UpdateAsset(BaseModel):
    name: str
    url: str
    size: int | None = None


class UpdateStatus(BaseModel):
    current_version: str
    latest_version: str | None = None
    update_available: bool = False
    channel: str = "stable"
    notes: str | None = None
    published_at: str | None = None
    asset: UpdateAsset | None = None
    last_check: float | None = None
    last_error: str | None = None
    download_path: str | None = None


def is_dev_version(version: str) -> bool:
    return "-dev." in version


def _parse_version(version: str) -> tuple[int, int, int, int | None]:
    match = _VERSION_RE.match(version.strip())
    if not match:
        return (0, 0, 0, None)
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    dev = match.group(4)
    return (major, minor, patch, int(dev) if dev is not None else None)


def is_newer_version(latest: str, current: str) -> bool:
    latest_tuple = _parse_version(latest)
    current_tuple = _parse_version(current)
    if latest_tuple[:3] != current_tuple[:3]:
        return latest_tuple[:3] > current_tuple[:3]
    latest_dev = latest_tuple[3]
    current_dev = current_tuple[3]
    if latest_dev is None and current_dev is not None:
        return True
    if latest_dev is not None and current_dev is None:
        return False
    if latest_dev is None and current_dev is None:
        return False
    return (latest_dev or 0) > (current_dev or 0)


def select_asset(assets: list[dict[str, Any]], platform: str) -> UpdateAsset | None:
    suffix = None
    if platform == "win32":
        suffix = ".exe"
    elif platform == "darwin":
        suffix = ".dmg"
    if not suffix:
        return None
    for asset in assets:
        name = str(asset.get("name", ""))
        if name.lower().endswith(suffix):
            return UpdateAsset(
                name=name,
                url=str(asset.get("browser_download_url", "")),
                size=asset.get("size"),
            )
    return None


def _update_log_path() -> Path:
    return logs_dir() / "update.log"


def _append_update_log(message: str) -> None:
    try:
        path = _update_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with path.open("a", encoding="utf-8", errors="ignore") as file:
            file.write(f"[{timestamp}] {message}\n")
    except Exception:
        logger.debug("写入 update.log 失败: {}", message)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class UpdateService:
    def __init__(
        self,
        owner: str = "gooderno1",
        repo: str = "LarkSync",
        config_manager: ConfigManager | None = None,
    ) -> None:
        self._owner = owner
        self._repo = repo
        self._config_manager = config_manager or ConfigManager.get()
        self._lock = asyncio.Lock()
        self._status_path = data_dir() / "updates" / "status.json"

    def load_cached_status(self) -> UpdateStatus:
        data = _read_json(self._status_path)
        current_version = get_version()
        if data:
            data.setdefault("current_version", current_version)
            if not data.get("last_check"):
                data["last_check"] = self._config_manager.config.last_update_check or None
            return UpdateStatus.model_validate(data)
        return UpdateStatus(current_version=current_version)

    async def check_for_updates(self, force: bool = False) -> UpdateStatus:
        async with self._lock:
            config = self._config_manager.config
            now = time.time()
            cached = self.load_cached_status()

            interval_hours = max(int(config.update_check_interval_hours or 24), 1)
            last_check = config.last_update_check or cached.last_check or 0.0

            if not force:
                if not config.auto_update_enabled:
                    return cached
                if last_check and (now - last_check) < (interval_hours * 3600):
                    return cached

            try:
                release = await self._fetch_latest_release()
                latest_version = str(release.get("tag_name") or "")
                if not latest_version or "-dev" in latest_version:
                    return self._save_status(
                        UpdateStatus(
                            current_version=get_version(),
                            latest_version=latest_version or None,
                            update_available=False,
                            channel="stable",
                            notes=None,
                            published_at=None,
                            asset=None,
                            last_check=now,
                            last_error="未找到稳定版本",
                        ),
                        now,
                    )

                allow_dev = bool(config.allow_dev_to_stable)
                current_version = get_version()
                update_available = is_newer_version(latest_version, current_version)
                if is_dev_version(current_version) and not allow_dev:
                    update_available = False

                asset = select_asset(release.get("assets") or [], sys.platform)

                status = UpdateStatus(
                    current_version=current_version,
                    latest_version=latest_version,
                    update_available=update_available,
                    channel="stable",
                    notes=release.get("body"),
                    published_at=release.get("published_at"),
                    asset=asset,
                    last_check=now,
                    last_error=None,
                )
                return self._save_status(status, now)
            except Exception as exc:
                message = str(exc)
                _append_update_log(f"检查更新失败: {message}")
                status = UpdateStatus(
                    current_version=get_version(),
                    latest_version=cached.latest_version,
                    update_available=False,
                    channel="stable",
                    notes=cached.notes,
                    published_at=cached.published_at,
                    asset=cached.asset,
                    last_check=now,
                    last_error=message,
                )
                return self._save_status(status, now)

    async def download_update(self) -> UpdateStatus:
        status = await self.check_for_updates(force=True)
        if not status.asset or not status.asset.url:
            raise RuntimeError("没有可下载的更新包")

        updates_dir = data_dir() / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        target_path = updates_dir / status.asset.name

        if target_path.exists() and status.asset.size:
            if target_path.stat().st_size == status.asset.size:
                status.download_path = str(target_path)
                return self._save_status(status, status.last_check or time.time())

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", status.asset.url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise RuntimeError(f"下载失败: HTTP {resp.status_code}")
                with target_path.open("wb") as file:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            file.write(chunk)

        status.download_path = str(target_path)
        _append_update_log(f"下载更新包完成: {target_path}")
        return self._save_status(status, status.last_check or time.time())

    async def _fetch_latest_release(self) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/releases/latest"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "LarkSync-Updater",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"获取 Release 失败: HTTP {resp.status_code}")
            return resp.json()

    def _save_status(self, status: UpdateStatus, last_check: float) -> UpdateStatus:
        self._persist_last_check(last_check)
        payload = status.model_dump()
        _write_json(self._status_path, payload)
        return status

    def _persist_last_check(self, last_check: float) -> None:
        path = self._config_manager.config_path
        data = _read_json(path)
        data["last_update_check"] = float(last_check)
        self._config_manager.save_config(data)
