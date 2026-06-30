"""Logging configuration for copilotmemory."""

import logging
import sys
from typing import Optional

from .config import get_settings


def setup_logger(
    name: str = "copilotmemory",
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name
        level: Logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    if level is None:
        settings = get_settings()
        level = settings.api_log_level

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Module-level logger
logger = setup_logger()
