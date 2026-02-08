from __future__ import annotations

from pathlib import Path

WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


def sanitize_path_segment(
    name: str,
    *,
    replacement: str = "_",
    check_reserved: bool = True,
) -> str:
    sanitized = "".join(
        replacement if (ord(ch) < 32 or ch in WINDOWS_INVALID_CHARS) else ch
        for ch in str(name)
    )
    sanitized = sanitized.rstrip(" .")
    if sanitized in {"", ".", ".."}:
        sanitized = replacement
    if check_reserved and sanitized.upper() in WINDOWS_RESERVED_NAMES:
        sanitized = f"{sanitized}_"
    return sanitized


def sanitize_filename(name: str, *, replacement: str = "_") -> str:
    value = str(name)
    path = Path(value)
    suffix = path.suffix
    if suffix and path.name != suffix:
        stem = path.name[: -len(suffix)]
    else:
        suffix = ""
        stem = path.name

    safe_stem = sanitize_path_segment(stem, replacement=replacement, check_reserved=True)
    if not suffix:
        return safe_stem

    ext = sanitize_path_segment(
        suffix[1:], replacement=replacement, check_reserved=False
    )
    if not ext:
        return safe_stem
    return f"{safe_stem}.{ext}"


__all__ = ["WINDOWS_INVALID_CHARS", "WINDOWS_RESERVED_NAMES", "sanitize_filename", "sanitize_path_segment"]
