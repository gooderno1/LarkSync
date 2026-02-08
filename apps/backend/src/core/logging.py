from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.core.paths import logs_dir

_LOG_FILE: Path | None = None


def init_logging(log_dir: Path | None = None) -> Path:
    """Initialize Loguru sinks for console + file logging."""
    resolved_dir = Path(log_dir) if log_dir is not None else logs_dir()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    log_file = resolved_dir / "larksync.log"

    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="INFO",
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        log_file,
        level="INFO",
        mode="a",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    logger.info("日志系统已初始化，写入路径: {}", log_file)
    global _LOG_FILE
    _LOG_FILE = log_file
    return log_file


def get_log_file() -> Path:
    if _LOG_FILE is not None:
        return _LOG_FILE
    return logs_dir() / "larksync.log"


__all__ = ["get_log_file", "init_logging"]
