from __future__ import annotations

import asyncio
import hashlib
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
    checksum_url: str | None = None
    sha256: str | None = None


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


def find_checksum_asset(
    assets: list[dict[str, Any]], target_asset_name: str
) -> UpdateAsset | None:
    target = target_asset_name.lower()
    exact_names = {f"{target}.sha256", f"{target}.sha256.txt"}
    candidates: list[UpdateAsset] = []

    for raw in assets:
        name = str(raw.get("name", ""))
        lower_name = name.lower()
        asset = UpdateAsset(
            name=name,
            url=str(raw.get("browser_download_url", "")),
            size=raw.get("size"),
        )
        if lower_name in exact_names:
            return asset
        if (
            lower_name.endswith(".sha256")
            or lower_name.endswith(".sha256.txt")
            or "sha256sum" in lower_name
        ):
            candidates.append(asset)

    if not candidates:
        return None
    # 常见命名：SHA256SUMS / checksums.txt，仅有一个时可直接使用。
    if len(candidates) == 1:
        return candidates[0]
    # 多个候选时，优先选择文件名包含目标安装包名的 checksum 文件。
    for candidate in candidates:
        if target in candidate.name.lower():
            return candidate
    return None


def extract_sha256_from_text(text: str, target_asset_name: str) -> str | None:
    target = target_asset_name.lower().strip()
    if not target:
        return None

    hash_with_name = re.compile(r"(?i)^([a-f0-9]{64})\s+\*?(.+)$")
    openssl_style = re.compile(r"(?i)^sha256\((.+)\)\s*=\s*([a-f0-9]{64})$")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = hash_with_name.match(line)
        if match:
            digest = match.group(1).lower()
            name = match.group(2).strip().strip("./").lower()
            if name == target or name.endswith(f"/{target}"):
                return digest
            continue
        match = openssl_style.match(line)
        if match:
            name = match.group(1).strip().strip("./").lower()
            digest = match.group(2).lower()
            if name == target or name.endswith(f"/{target}"):
                return digest

    all_hashes = re.findall(r"(?i)\b[a-f0-9]{64}\b", text)
    if len(all_hashes) == 1:
        return all_hashes[0].lower()
    return None


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    def auto_update_enabled(self) -> bool:
        return bool(self._config_manager.config.auto_update_enabled)

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
                if asset:
                    checksum_asset = find_checksum_asset(
                        release.get("assets") or [], asset.name
                    )
                    if checksum_asset:
                        asset.checksum_url = checksum_asset.url

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
        expected_sha256 = await self._resolve_expected_sha256(status.asset)

        updates_dir = data_dir() / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        target_path = updates_dir / status.asset.name

        if target_path.exists() and status.asset.size:
            if target_path.stat().st_size == status.asset.size:
                if compute_file_sha256(target_path) == expected_sha256:
                    status.download_path = str(target_path)
                    return self._save_status(status, status.last_check or time.time())
                _append_update_log(f"本地更新包校验失败，重新下载: {target_path}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", status.asset.url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise RuntimeError(f"下载失败: HTTP {resp.status_code}")
                with target_path.open("wb") as file:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            file.write(chunk)

        actual_sha256 = compute_file_sha256(target_path)
        if actual_sha256 != expected_sha256:
            target_path.unlink(missing_ok=True)
            raise RuntimeError("下载完成但 sha256 校验失败，已中止更新")

        status.download_path = str(target_path)
        _append_update_log(
            f"下载更新包完成: {target_path} (sha256={actual_sha256[:12]}...)"
        )
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

    async def _resolve_expected_sha256(self, asset: UpdateAsset) -> str:
        if asset.sha256:
            return asset.sha256.lower()
        if not asset.checksum_url:
            raise RuntimeError("更新包缺少 sha256 校验信息，已阻止下载")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(asset.checksum_url, follow_redirects=True)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"获取校验文件失败: HTTP {resp.status_code}"
                )
            checksum_text = resp.text
        digest = extract_sha256_from_text(checksum_text, asset.name)
        if not digest:
            raise RuntimeError("无法从校验文件解析目标安装包的 sha256")
        return digest
