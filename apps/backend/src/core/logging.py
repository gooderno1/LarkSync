from __future__ import annotations

from pathlib import Path

from loguru import logger


def init_logging(log_dir: Path | None = None) -> Path:
    """Initialize Loguru sinks for console + file logging."""
    root = Path(__file__).resolve().parents[4]
    resolved_dir = Path(log_dir) if log_dir is not None else root / "data" / "logs"
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
    return log_file


__all__ = ["init_logging"]
