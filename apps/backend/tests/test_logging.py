from pathlib import Path

from loguru import logger

from src.core.logging import init_logging


def test_init_logging_creates_file(tmp_path: Path) -> None:
    log_file = init_logging(tmp_path)
    logger.info("test message")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test message" in content
