from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import uuid
from functools import lru_cache
from pathlib import Path

from src.core.paths import data_dir


def _device_id_path() -> Path:
    return data_dir() / ".device_id"


def _normalize_device_id(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("empty device id")
    return cleaned


def _normalize_display_name(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("empty device display name")
    return cleaned


def _fingerprint_to_device_id(fingerprint: str) -> str:
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"dev-{digest[:24]}"


def _machine_fingerprint() -> str | None:
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore[attr-defined]

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
            if isinstance(value, str) and value.strip():
                return value.strip()
        except Exception:
            return None

    if sys.platform == "darwin":
        try:
            output = subprocess.check_output(
                [
                    "ioreg",
                    "-rd1",
                    "-c",
                    "IOPlatformExpertDevice",
                ],
                text=True,
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
            )
            marker = "IOPlatformUUID"
            for line in output.splitlines():
                if marker not in line:
                    continue
                _, _, tail = line.partition(marker)
                uuid_part = tail.split("=")[-1].strip().strip('"')
                if uuid_part:
                    return uuid_part
        except Exception:
            return None

    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            value = path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if value:
            return value
    return None


@lru_cache(maxsize=1)
def current_device_id() -> str:
    """获取当前设备标识：优先机器指纹，失败时回退到本地持久化随机值。"""
    env_value = os.getenv("LARKSYNC_DEVICE_ID")
    if env_value:
        return _normalize_device_id(env_value)

    machine_fp = _machine_fingerprint()
    if machine_fp:
        return _fingerprint_to_device_id(machine_fp)

    path = _device_id_path()
    if path.exists():
        try:
            return _normalize_device_id(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    device_id = f"dev-{uuid.uuid4().hex}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(device_id, encoding="utf-8")
    return device_id


@lru_cache(maxsize=1)
def current_device_name() -> str:
    env_value = os.getenv("LARKSYNC_DEVICE_NAME")
    if env_value:
        return _normalize_display_name(env_value)

    for candidate in (
        os.getenv("COMPUTERNAME"),
        os.getenv("HOSTNAME"),
        platform.node(),
    ):
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if candidate:
                return candidate
    return "当前设备"


__all__ = ["current_device_id", "current_device_name"]
