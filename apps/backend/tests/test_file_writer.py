import errno
from pathlib import Path

import pytest

import src.services.file_writer as file_writer_module
from src.services.file_writer import FileWriter


def test_write_markdown_sets_mtime(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "doc.md"
    content = "# 标题"
    mtime = 1700000000.0

    FileWriter.write_markdown(target, content, mtime)

    assert target.read_text(encoding="utf-8") == content
    assert abs(target.stat().st_mtime - mtime) < 1.0


def test_write_bytes_retries_when_file_is_temporarily_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "nested" / "locked.pdf"
    payload = b"pdf"
    mtime = 1700000001.0
    attempts = 0
    original_write_bytes = Path.write_bytes

    monkeypatch.setattr(file_writer_module.time, "sleep", lambda _: None)

    def flaky_write_bytes(self: Path, content: bytes) -> int:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise _build_locked_error(self)
        return original_write_bytes(self, content)

    monkeypatch.setattr(Path, "write_bytes", flaky_write_bytes)

    FileWriter.write_bytes(target, payload, mtime)

    assert attempts == 3
    assert target.read_bytes() == payload
    assert abs(target.stat().st_mtime - mtime) < 1.0


def test_write_bytes_raises_actionable_error_when_file_stays_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "nested" / "locked.pdf"
    attempts = 0

    monkeypatch.setattr(file_writer_module.time, "sleep", lambda _: None)

    def always_locked(self: Path, content: bytes) -> int:
        nonlocal attempts
        del content
        attempts += 1
        raise _build_locked_error(self)

    monkeypatch.setattr(Path, "write_bytes", always_locked)

    with pytest.raises(PermissionError, match="目标文件正被其他程序占用，请关闭后重试"):
        FileWriter.write_bytes(target, b"pdf", 1700000002.0)

    assert attempts == len(file_writer_module._LOCK_RETRY_DELAYS) + 1


def _build_locked_error(path: Path) -> PermissionError:
    error = PermissionError(
        errno.EACCES,
        "The process cannot access the file because it is being used by another process.",
        str(path),
    )
    error.winerror = 32
    return error
