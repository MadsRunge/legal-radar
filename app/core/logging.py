"""Structured logging setup using loguru."""

import sys

from loguru import logger


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure loguru for the application.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: Emit newline-delimited JSON instead of human-readable text.
    """
    logger.remove()

    if json_logs:
        logger.add(
            sys.stdout,
            level=level,
            serialize=True,
            enqueue=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
            colorize=True,
            enqueue=True,
        )

    logger.add(
        "logs/legal_radar.log",
        level=level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        serialize=json_logs,
        enqueue=True,
    )
