"""Structured logging setup for MotoDiag."""

import logging
import sys
from pathlib import Path


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output

    Returns:
        The root motodiag logger
    """
    global _initialized

    logger = logging.getLogger("motodiag")

    if _initialized:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _initialized = True
    logger.debug("Logging initialized (level=%s, file=%s)", level, log_file or "none")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the motodiag namespace."""
    return logging.getLogger(f"motodiag.{name}")


def reset_logging() -> None:
    """Reset logging state. Used in tests."""
    global _initialized
    logger = logging.getLogger("motodiag")
    logger.handlers.clear()
    _initialized = False
